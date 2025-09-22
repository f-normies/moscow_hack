import { Box, Container, Image, Input, Text } from "@chakra-ui/react"
import {
  Link as RouterLink,
  createFileRoute,
  redirect,
} from "@tanstack/react-router"
import { type SubmitHandler, useForm } from "react-hook-form"
import { FiLock, FiMail } from "react-icons/fi"

import type { Body_login_login_access_token as AccessToken } from "@/client"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import Logo from "/assets/images/fastapi-logo.svg"
import { emailPattern, passwordRules } from "../utils"
import Threads from "@/components/animations/backgrounds/Threads"

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
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AccessToken>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      username: "",
      password: "",
    },
  })

  const onSubmit: SubmitHandler<AccessToken> = async (data) => {
    if (isSubmitting) return

    resetError()

    try {
      await loginMutation.mutateAsync(data)
    } catch {
      // error is handled by useAuth hook
    }
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

      {/* Login Form Overlay */}
      <Container
        as="form"
        onSubmit={handleSubmit(onSubmit)}
        position="relative"
        zIndex={1}
        h="100vh"
        maxW="sm"
        alignItems="stretch"
        justifyContent="center"
        gap={4}
        centerContent
        bg="bg/80"
        backdropFilter="blur(10px)"
        borderRadius="lg"
        p={8}
        mx="auto"
        my={8}
      >
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
