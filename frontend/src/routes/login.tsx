import { Box, Container, Image, Input, Text, VStack, HStack, Separator } from "@chakra-ui/react"
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
  const { loginMutation, error, resetError } = useAuth()
  const [userHistory, setUserHistory] = useState<UserHistory[]>([])
  const [showHistory, setShowHistory] = useState(false)

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
      const result = await loginMutation.mutateAsync(data)
      // Save successful login to history
      if (result) {
        UserHistoryService.saveUserLogin({ email: data.username })
      }
    } catch {
      // error is handled by useAuth hook
    }
  }

  const handleUserHistorySelect = (user: UserHistory) => {
    setValue("username", user.email)
    setShowHistory(false)
  }

  const handleRemoveUser = (email: string) => {
    UserHistoryService.removeUser(email)
    const updatedHistory = UserHistoryService.getUserHistory()
    setUserHistory(updatedHistory)
    setShowHistory(updatedHistory.length > 0)
  }

  return (
    <Box position="relative" h="100vh" overflow="hidden">
      {/* Animated Background */}
      <Box
        position="absolute"
        top={0}
        left={0}
        right={0}
        bottom={0}
        zIndex={0}
      >
        <Threads
          color={[0, 0.588, 0.533]} // #009688 in RGB normalized (0/255, 150/255, 136/255)
          amplitude={0.6}
          distance={0.2}
          enableMouseInteraction={true}
        />
      </Box>

      {/* Main Content Container */}
      <Container
        position="relative"
        zIndex={1}
        h="100vh"
        maxW="4xl"
        display="flex"
        alignItems="center"
        justifyContent="center"
        gap={8}
        px={8}
      >
        {/* User History Cards */}
        {showHistory && (
          <VStack gap={4} align="stretch" flex="0 0 auto">
            <Text
              fontSize="lg"
              fontWeight="semibold"
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
            <Separator orientation="vertical" h="200px" mx={4} />
          </VStack>
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
          boxShadow="lg"
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
      </Container>
    </Box>
  )
}
