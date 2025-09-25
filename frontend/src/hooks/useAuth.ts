import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"

import {
  type Body_login_login_access_token as AccessToken,
  type ApiError,
  LoginService,
  type UserPublic,
  type UserRegister,
  UsersService,
} from "@/client"
import { handleError } from "@/utils"
import { UserHistoryService } from "@/utils/userHistory"

const isLoggedIn = () => {
  return localStorage.getItem("access_token") !== null
}

const useAuth = () => {
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: user } = useQuery<UserPublic | null, Error>({
    queryKey: ["currentUser"],
    queryFn: UsersService.readUserMe,
    enabled: isLoggedIn(),
  })

  const signUpMutation = useMutation({
    mutationFn: (data: UserRegister) =>
      UsersService.registerUser({ requestBody: data }),

    onSuccess: () => {
      navigate({ to: "/login" })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const login = async (data: AccessToken) => {
    const response = await LoginService.loginAccessToken({
      formData: data,
    })
    localStorage.setItem("access_token", response.access_token)

    // Return the token response so we can chain user data fetching
    return response
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: async (response, variables) => {
      // Save user history with token for automatic login
      UserHistoryService.saveUserLogin({
        email: variables.username,
        full_name: variables.username.split('@')[0] // Use email prefix as fallback name
      }, response.access_token)

      // Invalidate and refetch user data after successful login
      await queryClient.invalidateQueries({ queryKey: ["currentUser"] })
      navigate({ to: "/" })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const logout = () => {
    localStorage.removeItem("access_token")
    navigate({ to: "/login" })
  }

  const autoLogin = async (email: string) => {
    const storedToken = UserHistoryService.getStoredToken(email)
    if (!storedToken) {
      throw new Error("No stored token found")
    }

    // Set the token in localStorage
    localStorage.setItem("access_token", storedToken)

    try {
      // Validate the token by testing it
      await LoginService.testToken()

      // If valid, invalidate queries and navigate
      await queryClient.invalidateQueries({ queryKey: ["currentUser"] })
      navigate({ to: "/" })
    } catch (error) {
      // Token is invalid, remove it from storage and history
      localStorage.removeItem("access_token")
      UserHistoryService.removeUser(email)
      throw new Error("Stored token is invalid")
    }
  }

  return {
    signUpMutation,
    loginMutation,
    logout,
    autoLogin,
    user,
    error,
    resetError: () => setError(null),
  }
}

export { isLoggedIn }
export default useAuth
