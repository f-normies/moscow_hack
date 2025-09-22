import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  Spinner,
  Alert,
  Card,
  Flex,
  IconButton,
} from '@chakra-ui/react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { DicomService } from '../../client'
import type { DICOMStudyPublic } from '../../client'
import { LuTrash2, LuEye } from 'react-icons/lu'
import { toaster } from '../ui/toaster'

interface DICOMStudyListProps {
  onStudySelect?: (study: DICOMStudyPublic) => void
}

export function DICOMStudyList({ onStudySelect }: DICOMStudyListProps) {
  const queryClient = useQueryClient()
  // Using toaster instead of useToast for v3

  const { data: studies, isLoading, error } = useQuery({
    queryKey: ['dicom-studies'],
    queryFn: () => DicomService.listDicomStudies(),
  })

  const deleteMutation = useMutation({
    mutationFn: (studyId: string) => DicomService.deleteDicomStudy({ studyId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dicom-studies'] })
      toaster.create({
        title: 'Study deleted',
        description: 'DICOM study has been deleted successfully',
        type: 'success',
        duration: 3000,
      })
    },
    onError: (error: any) => {
      toaster.create({
        title: 'Delete failed',
        description: error.response?.data?.detail || 'Failed to delete study',
        type: 'error',
        duration: 5000,
      })
    },
  })

  const handleDeleteStudy = (study: DICOMStudyPublic, event: React.MouseEvent) => {
    event.stopPropagation()
    if (window.confirm(`Are you sure you want to delete study "${study.study_description || 'Unknown'}"?`)) {
      deleteMutation.mutate(study.id)
    }
  }

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString()
    } catch {
      return 'Unknown date'
    }
  }

  const getModalityColor = (modality?: string) => {
    const colors: Record<string, string> = {
      'CT': 'blue',
      'MRI': 'green',
      'XR': 'orange',
      'US': 'purple',
      'NM': 'pink',
      'PET': 'red',
      'MG': 'cyan',
    }
    return colors[modality || ''] || 'gray'
  }

  if (isLoading) {
    return (
      <Flex justify="center" align="center" minH="200px">
        <VStack gap={3}>
          <Spinner size="lg" color="blue.500" />
          <Text color="gray.600">Loading DICOM studies...</Text>
        </VStack>
      </Flex>
    )
  }

  if (error) {
    return (
      <Alert.Root status="error">
        <Alert.Indicator />
        <Alert.Description>
          <Box>
            <Text fontWeight="bold">Error loading DICOM studies</Text>
            <Text fontSize="sm">Please try refreshing the page</Text>
          </Box>
        </Alert.Description>
      </Alert.Root>
    )
  }

  if (!studies || studies.length === 0) {
    return (
      <Box textAlign="center" py={10}>
        <VStack gap={4}>
          <Text fontSize="lg" color="gray.600">
            No DICOM studies found
          </Text>
          <Text fontSize="sm" color="gray.500">
            Upload a ZIP file containing DICOM images to get started
          </Text>
        </VStack>
      </Box>
    )
  }

  return (
    <VStack gap={4} align="stretch" w="full">
      <Box>
        <Text fontSize="xl" fontWeight="bold" mb={2}>
          CT Studies ({studies.length})
        </Text>
        <Text fontSize="sm" color="gray.600">
          Your uploaded medical imaging studies
        </Text>
      </Box>

      {studies.map((study) => (
        <Card.Root
          key={study.id}
          variant="outline"
          cursor="pointer"
          transition="all 0.2s"
          _hover={{
            shadow: 'md',
            borderColor: 'blue.300',
          }}
          onClick={() => onStudySelect?.(study)}
        >
          <Card.Body>
            <Flex justify="space-between" align="start">
              <VStack align="start" gap={3} flex={1}>
                <HStack gap={3} wrap="wrap">
                  <Text fontSize="lg" fontWeight="bold">
                    {study.study_description || 'Unknown Study'}
                  </Text>
                  {study.modality && (
                    <Badge colorPalette={getModalityColor(study.modality)}>
                      {study.modality}
                    </Badge>
                  )}
                </HStack>

                <VStack align="start" gap={1}>
                  <HStack gap={6}>
                    <Text fontSize="sm" color="gray.600">
                      <Text as="span" fontWeight="medium">Patient ID:</Text>{' '}
                      {study.patient_id || 'Unknown'}
                    </Text>
                    {study.study_date && (
                      <Text fontSize="sm" color="gray.600">
                        <Text as="span" fontWeight="medium">Date:</Text>{' '}
                        {formatDate(study.study_date)}
                      </Text>
                    )}
                  </HStack>

                  <HStack gap={6}>
                    <Text fontSize="sm" color="gray.600">
                      <Text as="span" fontWeight="medium">Slices:</Text>{' '}
                      {study.file_count}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      <Text as="span" fontWeight="medium">Series:</Text>{' '}
                      {study.series?.length || 0}
                    </Text>
                  </HStack>

                  {study.institution_name && (
                    <Text fontSize="sm" color="gray.600">
                      <Text as="span" fontWeight="medium">Institution:</Text>{' '}
                      {study.institution_name}
                    </Text>
                  )}
                </VStack>
              </VStack>

              <HStack gap={2}>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => {
                    e.stopPropagation()
                    onStudySelect?.(study)
                  }}
                >
                  <LuEye /> View
                </Button>
                <IconButton
                  aria-label="Delete study"
                  size="sm"
                  variant="outline"
                  colorPalette="red"
                  loading={deleteMutation.isPending}
                  onClick={(e) => handleDeleteStudy(study, e)}
                >
                  <LuTrash2 />
                </IconButton>
              </HStack>
            </Flex>
          </Card.Body>
        </Card.Root>
      ))}
    </VStack>
  )
}