import React from 'react';
import { Card, Text, VStack, Avatar, Badge, IconButton } from '@chakra-ui/react';
import { FiX } from 'react-icons/fi';
import { UserHistory, UserHistoryService } from '@/utils/userHistory';
import { useColorModeValue } from '@/components/ui/color-mode';

interface UserHistoryCardProps {
  user: UserHistory;
  onSelect: (user: UserHistory) => void;
  onRemove: (email: string) => void;
}

export const UserHistoryCard: React.FC<UserHistoryCardProps> = ({
  user,
  onSelect,
  onRemove,
}) => {
  const handleCardClick = () => {
    onSelect(user);
  };

  // Color mode aware glow effects
  const glowShadow = useColorModeValue(
    "0 4px 12px rgba(0, 0, 0, 0.1)", // Light mode: subtle shadow
    "0 0 20px rgba(64, 255, 230, 0.3), 0 4px 12px rgba(0, 0, 0, 0.5)" // Dark mode: cyan glow + shadow
  );

  const hoverGlowShadow = useColorModeValue(
    "0 8px 20px rgba(0, 0, 0, 0.15)", // Light mode: enhanced shadow
    "0 0 30px rgba(64, 255, 230, 0.5), 0 8px 20px rgba(0, 0, 0, 0.7)" // Dark mode: stronger cyan glow + shadow
  );

  const handleRemoveClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRemove(user.email);
  };

  const formatName = (fullName: string) => {
    const words = fullName.split(' ');
    if (words.length >= 2) {
      return `${words[0]} ${words[1]}`;
    }
    return fullName;
  };

  return (
    <Card.Root
      variant="elevated"
      w="200px"
      h="280px"
      bg="bg/95"
      backdropFilter="blur(15px)"
      border="1px solid"
      borderColor="border.subtle"
      borderRadius="xl"
      position="relative"
      cursor="pointer"
      transition="all 0.3s"
      boxShadow={glowShadow}
      _hover={{
        transform: 'translateY(-4px)',
        boxShadow: hoverGlowShadow,
      }}
      onClick={handleCardClick}
    >

      {/* Remove button */}
      <IconButton
        aria-label="Remove user"
        size="xs"
        variant="ghost"
        position="absolute"
        top={2}
        right={2}
        zIndex={10}
        onClick={(e) => {
          e.stopPropagation();
          handleRemoveClick(e);
        }}
        colorPalette="gray"
      >
        <FiX />
      </IconButton>

      <Card.Body p={3} display="flex" flexDirection="column" justifyContent="space-between" h="100%">
        <VStack gap={2} align="center" flex="1" justify="center">
          {/* Avatar */}
          <Avatar.Root size="xl" colorPalette="teal">
            <Avatar.Fallback name={user.fullName} />
            {user.avatar && <Avatar.Image src={user.avatar} />}
          </Avatar.Root>

          {/* User Info */}
          <VStack gap={1} align="center" textAlign="center">
            <Text fontWeight="bold" fontSize="lg" lineHeight="short" color="fg" lineClamp={2}>
              {formatName(user.fullName)}
            </Text>

            {user.jobTitle && (
              <Text fontSize="sm" color="fg.muted" lineHeight="short" lineClamp={2}>
                {user.jobTitle}
              </Text>
            )}

            <Text fontSize="sm" color="fg.subtle" lineClamp={1}>
              {user.email}
            </Text>
          </VStack>
        </VStack>

        {/* Last Login Badge */}
        <Badge
          variant="subtle"
          colorPalette="teal"
          fontSize="xs"
          px={2}
          py={1}
          alignSelf="center"
          mt={2}
        >
          {UserHistoryService.formatLastLogin(user.lastLogin)}
        </Badge>
      </Card.Body>
    </Card.Root>
  );
};