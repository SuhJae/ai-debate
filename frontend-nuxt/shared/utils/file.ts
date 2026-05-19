export interface FileWithStatus {
  file: File
  id: string
  previewUrl: string
  status: 'uploading' | 'uploaded' | 'error'
  uploadedUrl?: string
  uploadedPathname?: string
  error?: string
}

export const FILE_UPLOAD_CONFIG = {
  maxSize: '8MB',
  types: ['image', 'application/pdf', 'text/csv'],
  acceptPattern: 'image/*,application/pdf,.csv,text/csv'
} as const

export function getFileIcon(mimeType: string, fileName?: string): string {
  if (mimeType.startsWith('image/')) return 'i-ph-image'
  if (mimeType === 'application/pdf') return 'i-ph-file-text'
  if (mimeType === 'text/csv' || fileName?.endsWith('.csv')) return 'i-ph-file-csv'
  return 'i-ph-file'
}

export function removeRandomSuffix(filename: string): string {
  return filename.replace(/^(.+)-[a-zA-Z0-9]+(\.[^.]+)$/, '$1$2')
}
