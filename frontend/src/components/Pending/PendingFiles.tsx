import { Skeleton, Table } from "@chakra-ui/react"

const PendingFiles = () => (
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
      {[...Array(5)].map((_, index) => (
        <Table.Row key={index}>
          <Table.Cell>
            <Skeleton h="20px" />
          </Table.Cell>
          <Table.Cell>
            <Skeleton h="20px" />
          </Table.Cell>
          <Table.Cell>
            <Skeleton h="20px" />
          </Table.Cell>
          <Table.Cell>
            <Skeleton h="20px" />
          </Table.Cell>
          <Table.Cell>
            <Skeleton h="20px" />
          </Table.Cell>
        </Table.Row>
      ))}
    </Table.Body>
  </Table.Root>
)

export default PendingFiles
