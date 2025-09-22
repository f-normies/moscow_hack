import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import {
  Box,
  Container,
  VStack,
  HStack,
  Text,
  Separator,
  Alert,
  Button,
} from '@chakra-ui/react'
import { LuEye, LuScan, LuBone } from 'react-icons/lu'

import { DICOMUploadForm, DICOMStudyList } from '../../components/DICOM'
import type { DICOMStudyPublic } from '../../client'

export const Route = createFileRoute('/_layout/dicom')({
  component: CTStudiesPage,
})

function CTStudiesPage() {
  const [selectedStudy, setSelectedStudy] = useState<DICOMStudyPublic | null>(null)
  const [viewMode, setViewMode] = useState<'dashboard' | 'original' | 'segmentations' | 'spine' | null>(null)

  const handleUploadComplete = (study: DICOMStudyPublic) => {
    // Auto-select the uploaded study for dashboard view
    setSelectedStudy(study)
    setViewMode('dashboard')
  }

  const handleStudySelect = (study: DICOMStudyPublic) => {
    setSelectedStudy(study)
    setViewMode('dashboard')
  }

  const handleBackToList = () => {
    setSelectedStudy(null)
    setViewMode(null)
  }

  const handleViewerMode = (mode: 'original' | 'segmentations' | 'spine') => {
    setViewMode(mode)
  }

  const renderDevelopmentAlert = (feature: string) => (
    <Alert.Root status="info" variant="subtle">
      <Alert.Indicator />
      <Alert.Description>
        <Text fontWeight="bold">{feature} Viewer</Text>
        <Text>This feature is currently in development. Coming soon!</Text>
      </Alert.Description>
    </Alert.Root>
  )

  // Study Dashboard View
  if (selectedStudy && viewMode === 'dashboard') {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack gap={6} align="stretch">
          {/* Header with Back Button */}
          <HStack justify="space-between">
            <Button
              variant="outline"
              onClick={handleBackToList}
              size="sm"
            >
              ← Back to CT Studies
            </Button>
            <Text fontSize="lg" fontWeight="semibold" color="fg.muted">
              Study Analysis Dashboard
            </Text>
          </HStack>

          {/* Study Metadata Card */}
          <Box
            bg="bg.subtle"
            p={6}
            borderRadius="lg"
            border="1px solid"
            borderColor="border.subtle"
          >
            <VStack gap={4} align="stretch">
              <Text fontSize="xl" fontWeight="bold">
                {selectedStudy.study_description || 'CT Study'}
              </Text>
              <HStack gap={8} wrap="wrap">
                <Text>
                  <Text as="span" fontWeight="medium">Patient ID:</Text>{' '}
                  {selectedStudy.patient_id}
                </Text>
                <Text>
                  <Text as="span" fontWeight="medium">Modality:</Text>{' '}
                  {selectedStudy.modality}
                </Text>
                <Text>
                  <Text as="span" fontWeight="medium">Files:</Text>{' '}
                  {selectedStudy.file_count}
                </Text>
                <Text>
                  <Text as="span" fontWeight="medium">Series:</Text>{' '}
                  {selectedStudy.series?.length || 0}
                </Text>
              </HStack>
            </VStack>
          </Box>

          {/* Viewer Mode Options */}
          <Box>
            <Text fontSize="lg" fontWeight="semibold" mb={4}>
              CT Study Viewer Modes
            </Text>
            <HStack gap={4} wrap="wrap">
              <Button
                onClick={() => handleViewerMode('original')}
                colorPalette="blue"
                variant="outline"
              >
                <LuEye /> Original DICOM
              </Button>
              <Button
                onClick={() => handleViewerMode('segmentations')}
                colorPalette="green"
                variant="outline"
              >
                <LuScan /> Segmentations
              </Button>
              <Button
                onClick={() => handleViewerMode('spine')}
                colorPalette="purple"
                variant="outline"
              >
                <LuBone /> Spine Analysis
              </Button>
            </HStack>
          </Box>
        </VStack>
      </Container>
    )
  }

  // Viewer Modes (Development Alerts)
  if (selectedStudy && viewMode && viewMode !== 'dashboard') {
    const viewerTitles = {
      original: 'Original DICOM',
      segmentations: 'Segmentations',
      spine: 'Spine Analysis'
    }

    return (
      <Container maxW="container.xl" py={8}>
        <VStack gap={6} align="stretch">
          <HStack justify="space-between">
            <Button
              variant="outline"
              onClick={() => setViewMode('dashboard')}
              size="sm"
            >
              ← Back to Dashboard
            </Button>
          </HStack>
          {renderDevelopmentAlert(viewerTitles[viewMode])}
        </VStack>
      </Container>
    )
  }

  // Main CT Studies Page
  return (
    <Container maxW="container.xl" py={8}>
      <VStack gap={8} align="stretch">
        {/* Unified Upload and Studies Interface */}
        <VStack gap={6} align="stretch">
          {/* Upload Section */}
          <Box>
            <Text fontSize="lg" fontWeight="semibold" mb={4}>
              Upload New CT Study
            </Text>
            <DICOMUploadForm onUploadComplete={handleUploadComplete} />
          </Box>

          <Separator />

          {/* Studies List Section */}
          <Box>
            <Text fontSize="lg" fontWeight="semibold" mb={4}>
              CT Studies
            </Text>
            <DICOMStudyList onStudySelect={handleStudySelect} />
          </Box>
        </VStack>
      </VStack>
    </Container>
  )
}