import { useMutation, useQueryClient } from "@tanstack/react-query"

import {
  Button,
  DialogActionTrigger,
  DialogTitle,
  FileUpload,
  Text,
  VStack,
  useFileUpload,
} from "@chakra-ui/react"
import { useState } from "react"
import { FaPlus } from "react-icons/fa"
import { HiUpload } from "react-icons/hi"

import { FilesService } from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTrigger,
} from "../ui/dialog"
const AddFile = () => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()

  const fileUpload = useFileUpload({
    maxFiles: 1,
    maxFileSize: 50 * 1024 * 1024, // 50MB
  })

  const mutation = useMutation({
    mutationFn: () => {
      const file = fileUpload.acceptedFiles[0]
      if (!file) {
        throw new Error("No file selected")
      }
      return FilesService.uploadFile({
        formData: { file },
      })
    },
    onSuccess: () => {
      showSuccessToast("File uploaded successfully.")
      fileUpload.clearFiles()
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["files"] })
    },
  })

  const handleUpload = () => {
    if (fileUpload.acceptedFiles.length > 0) {
      mutation.mutate()
    }
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "md" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button value="add-file" my={4}>
          <FaPlus fontSize="16px" />
          Upload File
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload File</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <Text mb={4}>Drag and drop a file or click to browse.</Text>
          <VStack gap={4}>
            <FileUpload.RootProvider value={fileUpload}>
              <FileUpload.HiddenInput />
              <FileUpload.Dropzone
                borderWidth="2px"
                borderStyle="dashed"
                borderRadius="md"
                p={6}
                width="full"
                display="flex"
                alignItems="center"
                justifyContent="center"
                _hover={{ borderColor: "blue.500" }}
              >
                <VStack gap={2}>
                  <HiUpload size={24} />
                  <FileUpload.DropzoneContent>
                    <Text fontWeight="semibold">Drop files here</Text>
                    <Text color="fg.muted" fontSize="sm">
                      or click to browse (max 50MB)
                    </Text>
                  </FileUpload.DropzoneContent>
                </VStack>
              </FileUpload.Dropzone>
              <FileUpload.List />
            </FileUpload.RootProvider>

            {fileUpload.rejectedFiles.length > 0 && (
              <Text color="red.500" fontSize="sm">
                {fileUpload.rejectedFiles.map((rejection) =>
                  `${rejection.file.name}: ${rejection.errors[0] || 'Invalid file'}`
                ).join(", ")}
              </Text>
            )}
          </VStack>
        </DialogBody>

        <DialogFooter gap={2}>
          <DialogActionTrigger asChild>
            <Button
              variant="subtle"
              colorPalette="gray"
              disabled={mutation.isPending}
            >
              Cancel
            </Button>
          </DialogActionTrigger>
          <Button
            variant="solid"
            onClick={handleUpload}
            disabled={fileUpload.acceptedFiles.length === 0}
            loading={mutation.isPending}
          >
            Upload
          </Button>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default AddFile
