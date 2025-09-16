import { Button, IconButton } from "@chakra-ui/react"
import { useMutation } from "@tanstack/react-query"
import { BsThreeDotsVertical } from "react-icons/bs"
import { FiDownload, FiInfo } from "react-icons/fi"

import type { FileMetadataPublic } from "@/client"
import { FilesService } from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { MenuContent, MenuRoot, MenuTrigger } from "../ui/menu"
import DeleteFile from "./DeleteFile"

interface FileActionsMenuProps {
  file: FileMetadataPublic
}

export const FileActionsMenu = ({ file }: FileActionsMenuProps) => {
  const { showSuccessToast } = useCustomToast()

  const downloadMutation = useMutation({
    mutationFn: () =>
      FilesService.getDownloadUrl({
        fileId: file.id,
        expiryHours: 1,
      }),
    onSuccess: (data) => {
      if (data.download_url) {
        window.open(data.download_url, "_blank")
        showSuccessToast("Download started.")
      }
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const handleDownload = () => {
    downloadMutation.mutate()
  }

  const handleViewInfo = () => {
    const info = `File: ${file.original_name}
Size: ${formatFileSize(file.size)}
Type: ${file.content_type}
Uploaded: ${new Date(file.created_at).toLocaleString()}
ID: ${file.id}`
    alert(info)
  }

  return (
    <MenuRoot>
      <MenuTrigger asChild>
        <IconButton variant="ghost" color="inherit">
          <BsThreeDotsVertical />
        </IconButton>
      </MenuTrigger>
      <MenuContent>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleViewInfo}
          justifyContent="flex-start"
          width="full"
        >
          <FiInfo fontSize="16px" />
          View Info
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDownload}
          disabled={downloadMutation.isPending}
          justifyContent="flex-start"
          width="full"
        >
          <FiDownload fontSize="16px" />
          {downloadMutation.isPending ? "Generating..." : "Download"}
        </Button>
        <DeleteFile id={file.id} filename={file.original_name} />
      </MenuContent>
    </MenuRoot>
  )
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes"
  const k = 1024
  const sizes = ["Bytes", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / k ** i).toFixed(1)} ${sizes[i]}`
}
