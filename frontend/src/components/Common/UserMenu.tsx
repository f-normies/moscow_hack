import { Box, Flex, Text, Avatar, HStack } from "@chakra-ui/react"
import { Link } from "@tanstack/react-router"
import { FiLogOut, FiUser } from "react-icons/fi"

import useAuth from "@/hooks/useAuth"
import { MenuContent, MenuItem, MenuRoot, MenuTrigger } from "../ui/menu"

const UserMenu = () => {
  const { user, logout } = useAuth()

  const handleLogout = async () => {
    logout()
  }

  return (
    <>
      {/* Desktop */}
      <Flex>
        <MenuRoot>
          <MenuTrigger asChild>
            <HStack
              data-testid="user-menu"
              cursor="pointer"
              p={2}
              gap={3}
              _hover={{
                bg: "gray.subtle",
                borderRadius: "md",
              }}
              transition="all 0.2s"
            >
              <Avatar.Root size="sm" colorPalette="teal">
                <Avatar.Fallback name={user?.full_name || "User"} />
                {user?.avatar && <Avatar.Image src={user.avatar} />}
              </Avatar.Root>
              <Text
                fontSize="sm"
                fontWeight="medium"
                maxW="120px"
                noOfLines={1}
                display={{ base: "none", md: "block" }}
              >
                {user?.full_name || "User"}
              </Text>
            </HStack>
          </MenuTrigger>

          <MenuContent>
            <Link to="settings">
              <MenuItem
                closeOnSelect
                value="user-settings"
                gap={2}
                py={2}
                style={{ cursor: "pointer" }}
              >
                <FiUser fontSize="18px" />
                <Box flex="1">My Profile</Box>
              </MenuItem>
            </Link>

            <MenuItem
              value="logout"
              gap={2}
              py={2}
              onClick={handleLogout}
              style={{ cursor: "pointer" }}
            >
              <FiLogOut />
              Log Out
            </MenuItem>
          </MenuContent>
        </MenuRoot>
      </Flex>
    </>
  )
}

export default UserMenu
