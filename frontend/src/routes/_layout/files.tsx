import {
  Container,
  EmptyState,
  Flex,
  Heading,
  Table,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { FiSearch } from "react-icons/fi"
import { z } from "zod"

import { FilesService } from "@/client"
import AddFile from "@/components/Files/AddFile"
import { FileActionsMenu } from "@/components/Files/FileActionsMenu"
import PendingFiles from "@/components/Pending/PendingFiles"
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPrevTrigger,
  PaginationRoot,
} from "@/components/ui/pagination.tsx"

const filesSearchSchema = z.object({
  page: z.number().catch(1),
})

const PER_PAGE = 5

function getFilesQueryOptions({ page }: { page: number }) {
  return {
    queryFn: () =>
      FilesService.listFiles({ skip: (page - 1) * PER_PAGE, limit: PER_PAGE }),
    queryKey: ["files", { page }],
  }
}

export const Route = createFileRoute("/_layout/files")({
  component: Files,
  validateSearch: (search) => filesSearchSchema.parse(search),
})

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes"
  const k = 1024
  const sizes = ["Bytes", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / k ** i).toFixed(1)} ${sizes[i]}`
}

function FilesTable() {
  const navigate = useNavigate({ from: Route.fullPath })
  const { page } = Route.useSearch()

  const { data, isLoading, isPlaceholderData } = useQuery({
    ...getFilesQueryOptions({ page }),
    placeholderData: (prevData) => prevData,
  })

  const setPage = (page: number) =>
    navigate({
      search: (prev: { [key: string]: string }) => ({ ...prev, page }),
    })

  const files = data?.data.slice(0, PER_PAGE) ?? []
  const count = data?.count ?? 0

  if (isLoading) {
    return <PendingFiles />
  }

  if (files.length === 0) {
    return (
      <EmptyState.Root>
        <EmptyState.Content>
          <EmptyState.Indicator>
            <FiSearch />
          </EmptyState.Indicator>
          <VStack textAlign="center">
            <EmptyState.Title>You don't have any files yet</EmptyState.Title>
            <EmptyState.Description>
              Upload a new file to get started
            </EmptyState.Description>
          </VStack>
        </EmptyState.Content>
      </EmptyState.Root>
    )
  }

  return (
    <>
      <Table.Root size={{ base: "sm", md: "md" }}>
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader w="40%">File Name</Table.ColumnHeader>
            <Table.ColumnHeader w="15%">Size</Table.ColumnHeader>
            <Table.ColumnHeader w="20%">Type</Table.ColumnHeader>
            <Table.ColumnHeader w="15%">Uploaded</Table.ColumnHeader>
            <Table.ColumnHeader w="10%">Actions</Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {files?.map((file) => (
            <Table.Row key={file.id} opacity={isPlaceholderData ? 0.5 : 1}>
              <Table.Cell truncate maxW="40%">
                {file.original_name}
              </Table.Cell>
              <Table.Cell>{formatFileSize(file.size)}</Table.Cell>
              <Table.Cell truncate maxW="20%">
                {file.content_type}
              </Table.Cell>
              <Table.Cell>
                {new Date(file.created_at).toLocaleDateString()}
              </Table.Cell>
              <Table.Cell width="10%">
                <FileActionsMenu file={file} />
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
      <Flex justifyContent="flex-end" mt={4}>
        <PaginationRoot
          count={count}
          pageSize={PER_PAGE}
          onPageChange={({ page }) => setPage(page)}
        >
          <Flex>
            <PaginationPrevTrigger />
            <PaginationItems />
            <PaginationNextTrigger />
          </Flex>
        </PaginationRoot>
      </Flex>
    </>
  )
}

function Files() {
  return (
    <Container maxW="full">
      <Heading size="lg" pt={12}>
        Files Management
      </Heading>
      <AddFile />
      <FilesTable />
    </Container>
  )
}
