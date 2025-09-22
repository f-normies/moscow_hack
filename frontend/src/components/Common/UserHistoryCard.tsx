import React from 'react';
import { Card, Text, HStack, VStack, Avatar, Badge } from '@chakra-ui/react';
import { FiX } from 'react-icons/fi';
import { IconButton } from '@/components/ui/button';
import GlareHover from '@/components/animations/interactive/GlareHover';
import { UserHistory, UserHistoryService } from '@/utils/userHistory';

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
    <GlareHover>
      <Card.Root
        variant="elevated"
        cursor="pointer"
        onClick={handleCardClick}
        transition="all 0.2s"
        _hover={{
          transform: 'translateY(-2px)',
          shadow: 'lg',
        }}
        position="relative"
        maxW="280px"
        bg="bg/90"
        backdropFilter="blur(10px)"
        borderColor="border.subtle"
      >
        {/* Remove button */}
        <IconButton
          aria-label="Remove user"
          size="xs"
          variant="ghost"
          position="absolute"
          top={2}
          right={2}
          zIndex={2}
          onClick={handleRemoveClick}
          colorPalette="gray"
        >
          <FiX />
        </IconButton>

        <Card.Body p={4}>
          <VStack gap={3} align="center">
            {/* Avatar */}
            <Avatar.Root size="lg" colorPalette="blue">
              <Avatar.Fallback name={user.fullName} />
              {user.avatar && <Avatar.Image src={user.avatar} />}
            </Avatar.Root>

            {/* User Info */}
            <VStack gap={1} align="center" textAlign="center">
              <Text fontWeight="semibold" fontSize="md" noOfLines={1}>
                {formatName(user.fullName)}
              </Text>

              {user.jobTitle && (
                <Text fontSize="sm" color="fg.muted" noOfLines={1}>
                  {user.jobTitle}
                </Text>
              )}

              <Text fontSize="xs" color="fg.subtle">
                {user.email}
              </Text>
            </VStack>

            {/* Last Login Badge */}
            <Badge
              variant="subtle"
              colorPalette="blue"
              fontSize="xs"
              px={2}
              py={1}
            >
              {UserHistoryService.formatLastLogin(user.lastLogin)}
            </Badge>
          </VStack>
        </Card.Body>
      </Card.Root>
    </GlareHover>
  );
};