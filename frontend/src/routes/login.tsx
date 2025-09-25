import { Box, Image, Input, Text, VStack, Separator } from "@chakra-ui/react"
import {
  Link as RouterLink,
  createFileRoute,
  redirect,
} from "@tanstack/react-router"
import { type SubmitHandler, useForm } from "react-hook-form"
import { FiLock, FiMail } from "react-icons/fi"
import { useState, useEffect } from "react"

import type { Body_login_login_access_token as AccessToken } from "@/client"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import Logo from "/assets/images/fastapi-logo.svg"
import { emailPattern, passwordRules } from "../utils"
import Threads from "@/components/animations/backgrounds/Threads"
import { UserHistoryCard } from "@/components/Common/UserHistoryCard"
import { UserHistory, UserHistoryService } from "@/utils/userHistory"
import { useColorModeValue } from "@/components/ui/color-mode"

export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
})

function Login() {
  const { loginMutation, autoLogin, error, resetError } = useAuth()
  const [userHistory, setUserHistory] = useState<UserHistory[]>([])
  const [showHistory, setShowHistory] = useState(false)

  // Color mode aware glow effects
  const loginFormGlow = useColorModeValue(
    "0 4px 20px rgba(0, 0, 0, 0.1)", // Light mode: subtle shadow
    "0 0 25px rgba(64, 255, 230, 0.2), 0 4px 20px rgba(0, 0, 0, 0.6)" // Dark mode: cyan glow + shadow
  );

  const separatorGlow = useColorModeValue(
    "none", // Light mode: no glow
    "0 0 15px rgba(64, 255, 230, 0.4)" // Dark mode: cyan glow
  );

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<AccessToken>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      username: "",
      password: "",
    },
  })

  // Load user history on component mount
  useEffect(() => {
    const history = UserHistoryService.getUserHistory()
    setUserHistory(history)
    setShowHistory(history.length > 0)
  }, [])

  const onSubmit: SubmitHandler<AccessToken> = async (data) => {
    if (isSubmitting) return

    resetError()

    try {
      await loginMutation.mutateAsync(data)
      // User history is now saved automatically in the useAuth hook
    } catch {
      // error is handled by useAuth hook
    }
  }

  const handleUserHistorySelect = async (user: UserHistory) => {
    if (isSubmitting) return

    resetError()

    try {
      // Attempt automatic login with stored token
      await autoLogin(user.email)
    } catch (error) {
      console.warn("Auto login failed, falling back to manual login:", error)

      // If auto login fails, fill form and focus password field
      setValue("username", user.email)
      setShowHistory(false)

      setTimeout(() => {
        const passwordField = document.getElementById("password") as HTMLInputElement
        if (passwordField) {
          passwordField.focus()
        }
      }, 150)
    }
  }

  const handleRemoveUser = (email: string) => {
    UserHistoryService.removeUser(email)
    const updatedHistory = UserHistoryService.getUserHistory()
    setUserHistory(updatedHistory)
    setShowHistory(updatedHistory.length > 0)
  }

  return (
    <Box position="relative" w="100vw" h="100vh" overflow="hidden">
      {/* Threads Background - Full Screen */}
      <Box
        position="fixed"
        top={0}
        left={0}
        w="100vw"
        h="100vh"
        zIndex={0}
      >
        <Threads
          amplitude={2}
          distance={0.6}
          enableMouseInteraction={true}
          style={{ width: "100%", height: "100%" }}
          blur={10.0}
        />
      </Box>

      {/* Main Content Overlay */}
      <Box
        position="relative"
        zIndex={1}
        w="100vw"
        h="100vh"
        display="flex"
        alignItems="center"
        justifyContent="center"
        px={8}
      >
        <Box
          w="100%"
          maxW="6xl"
          display="flex"
          alignItems="center"
          justifyContent="center"
          gap={8}
        >
        {/* User History Cards */}
        {showHistory && (
          <VStack gap={4} align="stretch" flex="0 0 auto">
            <Text
              fontSize="2xl"
              fontWeight="bold"
              color="fg"
              textAlign="center"
            >
              Welcome back
            </Text>
            <VStack gap={3}>
              {userHistory.map((user) => (
                <UserHistoryCard
                  key={user.email}
                  user={user}
                  onSelect={handleUserHistorySelect}
                  onRemove={handleRemoveUser}
                />
              ))}
            </VStack>
          </VStack>
        )}

        {/* Separator between history and login form */}
        {showHistory && (
          <Separator
            orientation="vertical"
            h="200px"
            mx={6}
            boxShadow={separatorGlow}
            transition="all 0.3s"
          />
        )}

        {/* Login Form */}
        <Box
          as="form"
          onSubmit={handleSubmit(onSubmit)}
          flex="0 0 auto"
          w="full"
          maxW="sm"
          bg="bg/80"
          backdropFilter="blur(10px)"
          borderRadius="lg"
          p={8}
          boxShadow={loginFormGlow}
        >
          <VStack gap={4} align="stretch">
            <Image
              src={Logo}
              alt="FastAPI logo"
              height="auto"
              maxW="2xs"
              alignSelf="center"
              mb={4}
            />
            <Field
              invalid={!!errors.username}
              errorText={errors.username?.message || !!error}
            >
              <InputGroup w="100%" startElement={<FiMail />}>
                <Input
                  id="username"
                  {...register("username", {
                    required: "Username is required",
                    pattern: emailPattern,
                  })}
                  placeholder="Email"
                  type="email"
                />
              </InputGroup>
            </Field>
            <PasswordInput
              id="password"
              type="password"
              startElement={<FiLock />}
              {...register("password", passwordRules())}
              placeholder="Password"
              errors={errors}
            />
            <RouterLink to="/recover-password" className="main-link">
              Forgot Password?
            </RouterLink>
            <Button variant="solid" type="submit" loading={isSubmitting} size="md">
              Log In
            </Button>
            <Text textAlign="center">
              Don't have an account?{" "}
              <RouterLink to="/signup" className="main-link">
                Sign Up
              </RouterLink>
            </Text>
          </VStack>
        </Box>
        </Box>
      </Box>
    </Box>
  )
}
