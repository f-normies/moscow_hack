import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import {
  Box,
  Container,
  VStack,
  HStack,
  Text,
  Tabs,
} from '@chakra-ui/react'
import { LuPlus } from 'react-icons/lu'

import { DICOMUploadForm, DICOMStudyList, DICOMStudyViewer } from '../../components/DICOM'
import type { DICOMStudyPublic } from '../../client'

export const Route = createFileRoute('/_layout/dicom')({
  component: DICOMPage,
})

function DICOMPage() {
  const [selectedStudy, setSelectedStudy] = useState<DICOMStudyPublic | null>(null)
  const [activeTab, setActiveTab] = useState('0')

  const handleUploadComplete = (study: DICOMStudyPublic) => {
    // Switch to studies tab and select the uploaded study
    setActiveTab('1')
    setSelectedStudy(study)
  }

  const handleStudySelect = (study: DICOMStudyPublic) => {
    setSelectedStudy(study)
  }

  const handleBackToList = () => {
    setSelectedStudy(null)
  }

  if (selectedStudy) {
    return (
      <Container maxW="container.xl" py={8}>
        <DICOMStudyViewer
          studyId={selectedStudy.id}
          onBack={handleBackToList}
        />
      </Container>
    )
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack gap={8} align="stretch">
        {/* Header */}
        <Box>
          <Text fontSize="3xl" fontWeight="bold" mb={2}>
            DICOM Studies
          </Text>
          <Text fontSize="lg" color="gray.600">
            Upload and manage medical imaging studies
          </Text>
        </Box>

        {/* Main Content */}
        <Tabs.Root value={activeTab} onValueChange={(details) => setActiveTab(details.value || '0')}>
          <Tabs.List>
            <Tabs.Trigger value="0">
              <HStack gap={2}>
                <LuPlus size={12} />
                <Text>Upload Study</Text>
              </HStack>
            </Tabs.Trigger>
            <Tabs.Trigger value="1">My Studies</Tabs.Trigger>
          </Tabs.List>

          <Tabs.ContentGroup>
            {/* Upload Tab */}
            <Tabs.Content value="0" px={0}>
              <VStack gap={8} align="stretch">
                <Box>
                  <Text fontSize="xl" fontWeight="bold" mb={2}>
                    Upload New DICOM Study
                  </Text>
                  <Text color="gray.600" mb={6}>
                    Upload a ZIP archive containing DICOM medical imaging files
                  </Text>
                </Box>

                <Box display="flex" justifyContent="center">
                  <DICOMUploadForm onUploadComplete={handleUploadComplete} />
                </Box>
              </VStack>
            </Tabs.Content>

            {/* Studies List Tab */}
            <Tabs.Content value="1" px={0}>
              <DICOMStudyList onStudySelect={handleStudySelect} />
            </Tabs.Content>
          </Tabs.ContentGroup>
        </Tabs.Root>
      </VStack>
    </Container>
  )
}