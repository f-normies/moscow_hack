import { useState } from 'react'
import {
  Box,
  Button,
  VStack,
  Text,
  Progress,
  Alert,
  Input,
  Field,
} from '@chakra-ui/react'
import { toaster } from '../ui/toaster'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { DicomService } from '../../client'
import type { DICOMStudyPublic } from '../../client'

interface DICOMUploadFormProps {
  onUploadComplete?: (study: DICOMStudyPublic) => void
}

export function DICOMUploadForm({ onUploadComplete }: DICOMUploadFormProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const queryClient = useQueryClient()
  // Using toaster instead of useToast for v3

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      return DicomService.uploadDicomZip({
        formData: { file },
      })
    },
    onSuccess: (study) => {
      queryClient.invalidateQueries({ queryKey: ['dicom-studies'] })
      toaster.create({
        title: 'Upload successful',
        description: `DICOM study "${study.study_description || 'Unknown'}" uploaded successfully`,
        type: 'success',
        duration: 5000,
      })
      onUploadComplete?.(study)
      setSelectedFile(null)
    },
    onError: (error: any) => {
      console.error('Upload failed:', error)
      toaster.create({
        title: 'Upload failed',
        description: error.response?.data?.detail || 'Failed to upload DICOM file',
        type: 'error',
        duration: 5000,
      })
    },
  })

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      validateAndSetFile(file)
    }
  }

  const validateAndSetFile = (file: File) => {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.zip')) {
      toaster.create({
        title: 'Invalid file type',
        description: 'Please select a ZIP file containing DICOM images',
        type: 'error',
        duration: 3000,
      })
      return
    }

    // Validate file size (1GB limit)
    if (file.size > 1024 * 1024 * 1024) {
      toaster.create({
        title: 'File too large',
        description: 'File size must be less than 1GB',
        type: 'error',
        duration: 3000,
      })
      return
    }

    setSelectedFile(file)
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0])
    }
  }

  const handleUpload = () => {
    if (selectedFile) {
      uploadMutation.mutate(selectedFile)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <VStack gap={6} align="center" w="full" maxW="500px" mx="auto">

      <Field.Root>
        <Field.Label color="fg">DICOM ZIP Archive</Field.Label>
        <Box
          position="relative"
          border="2px"
          borderColor={dragActive ? 'ui.main' : 'border.muted'}
          borderStyle="dashed"
          borderRadius="lg"
          p={12}
          textAlign="center"
          bg={dragActive ? 'bg.subtle' : 'bg.muted'}
          transition="all 0.2s"
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          cursor="pointer"
          _hover={{ borderColor: 'ui.main', bg: 'bg.subtle' }}
          w="full"
          aspectRatio="1.2"
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <Input
            type="file"
            accept=".zip"
            onChange={handleFileSelect}
            position="absolute"
            top={0}
            left={0}
            width="100%"
            height="100%"
            opacity={0}
            cursor="pointer"
          />

          <VStack gap={4}>
            <Text fontSize="lg" color="fg.muted" fontWeight="medium">
              {dragActive ? 'Drop ZIP file here' : 'Click to select or drag and drop'}
            </Text>
            <Text fontSize="sm" color="fg.subtle">
              ZIP files up to 1GB containing DICOM images
            </Text>
          </VStack>
        </Box>

        {selectedFile && (
          <Box mt={4} p={4} bg="bg.subtle" borderRadius="md" border="1px solid" borderColor="border.subtle">
            <VStack align="start" gap={2}>
              <Text fontWeight="medium" color="fg">{selectedFile.name}</Text>
              <Text fontSize="sm" color="fg.muted">
                Size: {formatFileSize(selectedFile.size)}
              </Text>
            </VStack>
          </Box>
        )}

        <Field.HelperText color="fg.subtle">
          Supported format: ZIP archives containing DICOM files (.dcm, .dicom)
        </Field.HelperText>
      </Field.Root>

      {uploadMutation.isPending && (
        <Box>
          <Text fontSize="sm" mb={2} color="ui.main">
            Processing DICOM files...
          </Text>
          <Progress.Root size="lg" value={null} colorPalette="blue">
            <Progress.Track>
              <Progress.Range />
            </Progress.Track>
          </Progress.Root>
        </Box>
      )}

      {uploadMutation.isError && (
        <Alert.Root status="error">
          <Alert.Indicator />
          <Alert.Description>
            Upload failed. Please check your file and try again.
          </Alert.Description>
        </Alert.Root>
      )}

      {uploadMutation.isSuccess && (
        <Alert.Root status="success">
          <Alert.Indicator />
          <Alert.Description>
            DICOM study uploaded and processed successfully!
          </Alert.Description>
        </Alert.Root>
      )}

      <Button
        onClick={handleUpload}
        disabled={!selectedFile || uploadMutation.isPending}
        loading={uploadMutation.isPending}
        loadingText="Processing..."
colorPalette="teal"
        size="lg"
      >
        Upload DICOM Study
      </Button>
    </VStack>
  )
}