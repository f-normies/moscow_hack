import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  Spinner,
  Alert,
  Tabs,
  Card,
  Separator,
  SimpleGrid,
  Stat,
  Accordion,
  Table,
  Flex,
} from '@chakra-ui/react'
import { useQuery } from '@tanstack/react-query'
import { LuArrowLeft } from 'react-icons/lu'
import { DicomService } from '../../client'
import type { DICOMSeriesPublic } from '../../client'

interface DICOMStudyViewerProps {
  studyId: string
  onBack?: () => void
}

interface SeriesViewerProps {
  series: DICOMSeriesPublic
}

function SeriesViewer({ series }: SeriesViewerProps) {
  const { data: metadata, isLoading } = useQuery({
    queryKey: ['dicom-series-metadata', series.id],
    queryFn: () => DicomService.getSeriesMetadata({ seriesId: series.id }),
  })

  const formatValue = (value: any) => {
    if (value === null || value === undefined) return 'N/A'
    if (typeof value === 'string' && value.trim() === '') return 'N/A'
    return String(value)
  }

  if (isLoading) {
    return (
      <Flex justify="center" py={8}>
        <Spinner />
      </Flex>
    )
  }

  return (
    <VStack gap={6} align="stretch">
      {/* Series Overview */}
      <Card.Root variant="outline">
        <Card.Body>
          <VStack align="start" gap={4}>
            <HStack gap={3}>
              <Text fontSize="lg" fontWeight="bold">
                {series.series_description || `Series ${series.series_number || 'Unknown'}`}
              </Text>
              {series.modality && (
                <Badge colorPalette="blue">{series.modality}</Badge>
              )}
            </HStack>

            <SimpleGrid columns={{ base: 1, md: 3 }} gap={4} w="full">
              <Stat.Root>
                <Stat.Label>Series Number</Stat.Label>
                <Stat.ValueText>{series.series_number || 'N/A'}</Stat.ValueText>
              </Stat.Root>
              <Stat.Root>
                <Stat.Label>Body Part</Stat.Label>
                <Stat.ValueText fontSize="md">
                  {series.body_part_examined || 'N/A'}
                </Stat.ValueText>
              </Stat.Root>
              <Stat.Root>
                <Stat.Label>Image Count</Stat.Label>
                <Stat.ValueText>{series.image_count}</Stat.ValueText>
              </Stat.Root>
            </SimpleGrid>
          </VStack>
        </Card.Body>
      </Card.Root>

      {/* Image Metadata */}
      {metadata && metadata.length > 0 && (
        <Card.Root variant="outline">
          <Card.Body>
            <Text fontSize="md" fontWeight="bold" mb={4}>
              Image Metadata ({metadata.length} images)
            </Text>

            <Accordion.Root collapsible>
              <Accordion.Item value="metadata">
                <Accordion.ItemTrigger>
                  <Box flex="1" textAlign="left">
                    <Text fontWeight="medium">View Detailed Metadata</Text>
                  </Box>
                  <Accordion.ItemIndicator />
                </Accordion.ItemTrigger>
                <Accordion.ItemContent>
                  <Accordion.ItemBody pb={4}>
                    <Table.Root size="sm" variant="outline">
                      <Table.Header>
                        <Table.Row>
                          <Table.ColumnHeader>Instance</Table.ColumnHeader>
                          <Table.ColumnHeader>Dimensions</Table.ColumnHeader>
                          <Table.ColumnHeader>Pixel Spacing</Table.ColumnHeader>
                          <Table.ColumnHeader>Slice Thickness</Table.ColumnHeader>
                          <Table.ColumnHeader>Window Center</Table.ColumnHeader>
                          <Table.ColumnHeader>Window Width</Table.ColumnHeader>
                        </Table.Row>
                      </Table.Header>
                      <Table.Body>
                        {metadata.slice(0, 10).map((meta) => (
                          <Table.Row key={meta.id}>
                            <Table.Cell>{meta.instance_number || 'N/A'}</Table.Cell>
                            <Table.Cell>
                              {meta.rows && meta.columns
                                ? `${meta.rows} × ${meta.columns}`
                                : 'N/A'}
                            </Table.Cell>
                            <Table.Cell>{formatValue(meta.pixel_spacing)}</Table.Cell>
                            <Table.Cell>{formatValue(meta.slice_thickness)}</Table.Cell>
                            <Table.Cell>{formatValue(meta.window_center)}</Table.Cell>
                            <Table.Cell>{formatValue(meta.window_width)}</Table.Cell>
                          </Table.Row>
                        ))}
                      </Table.Body>
                    </Table.Root>
                    {metadata.length > 10 && (
                      <Text fontSize="sm" color="gray.600" mt={2}>
                        Showing first 10 of {metadata.length} images
                      </Text>
                    )}
                  </Accordion.ItemBody>
                </Accordion.ItemContent>
              </Accordion.Item>

              {/* Sample DICOM Tags */}
              {metadata[0]?.extracted_metadata && (
                <Accordion.Item value="dicom-tags">
                  <Accordion.ItemTrigger>
                    <Box flex="1" textAlign="left">
                      <Text fontWeight="medium">DICOM Tags (Sample from first image)</Text>
                    </Box>
                    <Accordion.ItemIndicator />
                  </Accordion.ItemTrigger>
                  <Accordion.ItemContent>
                    <Accordion.ItemBody pb={4}>
                      <Table.Root size="sm" variant="outline">
                        <Table.Header>
                          <Table.Row>
                            <Table.ColumnHeader>Tag</Table.ColumnHeader>
                            <Table.ColumnHeader>Value</Table.ColumnHeader>
                          </Table.Row>
                        </Table.Header>
                        <Table.Body>
                          {Object.entries(metadata[0].extracted_metadata).map(([key, value]) => (
                            <Table.Row key={key}>
                              <Table.Cell fontWeight="medium">{key}</Table.Cell>
                              <Table.Cell>{formatValue(value)}</Table.Cell>
                            </Table.Row>
                          ))}
                        </Table.Body>
                      </Table.Root>
                    </Accordion.ItemBody>
                  </Accordion.ItemContent>
                </Accordion.Item>
              )}
            </Accordion.Root>
          </Card.Body>
        </Card.Root>
      )}

      {/* Future: Image Viewer Placeholder */}
      <Card.Root variant="outline" bg="gray.50">
        <Card.Body>
          <VStack gap={3} py={8}>
            <Text fontSize="lg" fontWeight="medium" color="gray.600">
              Image Viewer
            </Text>
            <Text fontSize="sm" color="gray.500" textAlign="center">
              DICOM image viewing capabilities will be implemented in future versions.
              <br />
              For now, you can download individual files through the file management system.
            </Text>
          </VStack>
        </Card.Body>
      </Card.Root>
    </VStack>
  )
}

export function DICOMStudyViewer({ studyId, onBack }: DICOMStudyViewerProps) {
  const { data: study, isLoading, error } = useQuery({
    queryKey: ['dicom-study', studyId],
    queryFn: () => DicomService.getDicomStudy({ studyId }),
  })

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    } catch {
      return 'Unknown date'
    }
  }

  if (isLoading) {
    return (
      <Flex justify="center" align="center" minH="400px">
        <VStack gap={3}>
          <Spinner size="lg" color="blue.500" />
          <Text color="gray.600">Loading DICOM study...</Text>
        </VStack>
      </Flex>
    )
  }

  if (error || !study) {
    return (
      <Alert.Root status="error">
        <Alert.Indicator />
        <Alert.Description>
          <VStack align="start">
            <Text fontWeight="bold">Error loading DICOM study</Text>
            <Text fontSize="sm">The study could not be found or loaded</Text>
          </VStack>
        </Alert.Description>
      </Alert.Root>
    )
  }

  return (
    <VStack gap={6} align="stretch" w="full">
      {/* Header */}
      <HStack>
        {onBack && (
          <Button onClick={onBack} variant="ghost">
            <LuArrowLeft /> Back to Studies
          </Button>
        )}
      </HStack>

      {/* Study Information */}
      <Card.Root variant="outline">
        <Card.Body>
          <VStack align="start" gap={4}>
            <HStack gap={3} wrap="wrap">
              <Text fontSize="2xl" fontWeight="bold">
                {study.study_description || 'Unknown Study'}
              </Text>
              {study.modality && (
                <Badge colorPalette="blue" fontSize="md" px={3} py={1}>
                  {study.modality}
                </Badge>
              )}
            </HStack>

            <Separator />

            <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} gap={6} w="full">
              <Stat.Root>
                <Stat.Label>Patient ID</Stat.Label>
                <Stat.ValueText fontSize="lg">
                  {study.patient_id || 'Unknown'}
                </Stat.ValueText>
              </Stat.Root>
              <Stat.Root>
                <Stat.Label>Study Date</Stat.Label>
                <Stat.ValueText fontSize="lg">
                  {study.study_date ? formatDate(study.study_date) : 'Unknown'}
                </Stat.ValueText>
              </Stat.Root>
              <Stat.Root>
                <Stat.Label>Total Files</Stat.Label>
                <Stat.ValueText fontSize="lg">{study.file_count}</Stat.ValueText>
              </Stat.Root>
              <Stat.Root>
                <Stat.Label>Series Count</Stat.Label>
                <Stat.ValueText fontSize="lg">
                  {study.series?.length || 0}
                </Stat.ValueText>
              </Stat.Root>
            </SimpleGrid>

            {study.institution_name && (
              <>
                <Separator />
                <Box>
                  <Text fontSize="sm" color="gray.600" fontWeight="medium">
                    Institution
                  </Text>
                  <Text fontSize="md">{study.institution_name}</Text>
                </Box>
              </>
            )}
          </VStack>
        </Card.Body>
      </Card.Root>

      {/* Series Tabs */}
      {study.series && study.series.length > 0 ? (
        <Card.Root variant="outline">
          <Card.Body>
            <Text fontSize="lg" fontWeight="bold" mb={4}>
              Series ({study.series.length})
            </Text>
            <Tabs.Root defaultValue={study.series[0]?.id}>
              <Tabs.List>
                {study.series.map((series, index) => (
                  <Tabs.Trigger key={series.id} value={series.id}>
                    Series {series.series_number || index + 1}
                    {series.modality && (
                      <Badge ml={2} fontSize="xs">
                        {series.modality}
                      </Badge>
                    )}
                  </Tabs.Trigger>
                ))}
              </Tabs.List>

              <Tabs.ContentGroup>
                {study.series.map((series) => (
                  <Tabs.Content key={series.id} value={series.id} px={0}>
                    <SeriesViewer series={series} />
                  </Tabs.Content>
                ))}
              </Tabs.ContentGroup>
            </Tabs.Root>
          </Card.Body>
        </Card.Root>
      ) : (
        <Alert.Root status="info">
          <Alert.Indicator />
          <Alert.Description>
            <Text>No series found in this study</Text>
          </Alert.Description>
        </Alert.Root>
      )}
    </VStack>
  )
}