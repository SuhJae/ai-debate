<script setup lang="ts">
import type { GlobalMcpServer } from '~/types/debate-state'

type Transport = GlobalMcpServer['transport']

const config = useRuntimeConfig()
const toast = useToast()

const transportItems: { label: string, value: Transport }[] = [
  { label: 'stdio', value: 'stdio' },
  { label: 'http', value: 'http' },
  { label: 'sse', value: 'sse' }
]

const name = ref('')
const description = ref('')
const transport = ref<Transport>('stdio')
const commandOrUrl = ref('')
const argsText = ref('')
const envText = ref('')
const headersText = ref('')
const enabled = ref(true)
const trusted = ref(false)
const creating = ref(false)
const updatingServerId = ref<string | null>(null)
const deletingServerId = ref<string | null>(null)

const {
  data: servers,
  pending,
  refresh
} = useFetch<GlobalMcpServer[]>(
  `${config.public.aiDebateApiUrl}/mcp/servers`,
  {
    key: 'global-mcp-servers',
    server: false,
    default: () => []
  }
)

const activeCount = computed(() => (servers.value ?? []).filter(server => server.enabled).length)
const commandLabel = computed(() => transport.value === 'stdio' ? 'Command' : 'URL')

async function createServer() {
  if (creating.value) return

  let env: Record<string, string>
  let headers: Record<string, string>
  try {
    env = parseKeyValueLines(envText.value, 'Environment')
    headers = parseKeyValueLines(headersText.value, 'Headers')
  } catch (error) {
    toast.add({
      title: 'MCP server was not added',
      description: error instanceof Error ? error.message : 'Check the server fields.',
      color: 'error',
      icon: 'i-ph-warning'
    })
    return
  }

  creating.value = true
  try {
    const server = await $fetch<GlobalMcpServer>(
      `${config.public.aiDebateApiUrl}/mcp/servers`,
      {
        method: 'POST',
        body: {
          name: name.value.trim(),
          description: description.value.trim(),
          transport: transport.value,
          command_or_url: commandOrUrl.value.trim(),
          args: parseArgs(argsText.value),
          env,
          headers,
          enabled: enabled.value,
          trusted: trusted.value
        }
      }
    )
    servers.value = [...(servers.value ?? []), server]
    resetForm()
  } catch (error) {
    toast.add({
      title: 'MCP server was not added',
      description: error instanceof Error ? error.message : 'The API rejected the server.',
      color: 'error',
      icon: 'i-ph-warning'
    })
  } finally {
    creating.value = false
  }
}

async function patchServer(server: GlobalMcpServer, patch: Partial<GlobalMcpServer>) {
  updatingServerId.value = server.id
  try {
    const updated = await $fetch<GlobalMcpServer>(
      `${config.public.aiDebateApiUrl}/mcp/servers/${server.id}`,
      {
        method: 'PATCH',
        body: patch
      }
    )
    servers.value = (servers.value ?? []).map(item => item.id === updated.id ? updated : item)
  } catch (error) {
    toast.add({
      title: 'MCP server was not updated',
      description: error instanceof Error ? error.message : 'The API rejected the update.',
      color: 'error',
      icon: 'i-ph-warning'
    })
    await refresh()
  } finally {
    updatingServerId.value = null
  }
}

async function deleteServer(server: GlobalMcpServer) {
  deletingServerId.value = server.id
  try {
    await $fetch(`${config.public.aiDebateApiUrl}/mcp/servers/${server.id}`, {
      method: 'DELETE'
    })
    servers.value = (servers.value ?? []).filter(item => item.id !== server.id)
  } catch (error) {
    toast.add({
      title: 'MCP server was not deleted',
      description: error instanceof Error ? error.message : 'The API rejected the delete.',
      color: 'error',
      icon: 'i-ph-warning'
    })
  } finally {
    deletingServerId.value = null
  }
}

function resetForm() {
  name.value = ''
  description.value = ''
  transport.value = 'stdio'
  commandOrUrl.value = ''
  argsText.value = ''
  envText.value = ''
  headersText.value = ''
  enabled.value = true
  trusted.value = false
}

function parseArgs(value: string) {
  return value
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
}

function parseKeyValueLines(value: string, label: string) {
  const entries: Record<string, string> = {}
  for (const rawLine of value.split('\n')) {
    const line = rawLine.trim()
    if (!line) continue
    const separator = line.indexOf('=')
    if (separator <= 0) {
      throw new Error(`${label} entries must use KEY=value.`)
    }
    const key = line.slice(0, separator).trim()
    if (!key) {
      throw new Error(`${label} entries must include a key.`)
    }
    entries[key] = line.slice(separator + 1).trim()
  }
  return entries
}

function serverEndpoint(server: GlobalMcpServer) {
  if (server.transport === 'stdio') {
    return [server.command_or_url, ...server.args].filter(Boolean).join(' ')
  }
  return server.command_or_url
}
</script>

<template>
  <section class="grid gap-3 border-b border-default pb-4">
    <div class="flex min-w-0 flex-wrap items-center gap-2">
      <div class="min-w-0 flex-1">
        <div class="truncate text-sm font-semibold text-highlighted">
          MCP Servers
        </div>
        <div class="truncate text-xs text-muted">
          {{ activeCount }} enabled globally
        </div>
      </div>
      <UButton
        icon="i-ph-arrow-clockwise"
        color="neutral"
        variant="ghost"
        size="xs"
        :loading="pending"
        @click="() => refresh()"
      />
      <UPopover :content="{ align: 'end', sideOffset: 8 }">
        <UButton
          icon="i-ph-plus"
          size="xs"
        >
          Add
        </UButton>

        <template #content>
          <div class="grid w-80 content-start gap-2.5 p-3">
            <div class="text-sm font-semibold text-highlighted">
              Add MCP Server
            </div>
            <UFormField label="Name">
              <UInput
                v-model="name"
                class="w-full"
                placeholder="filesystem"
              />
            </UFormField>
            <UFormField label="Transport">
              <USelect
                v-model="transport"
                :items="transportItems"
                class="w-full"
              />
            </UFormField>
            <UFormField :label="commandLabel">
              <UInput
                v-model="commandOrUrl"
                class="w-full"
                :placeholder="transport === 'stdio' ? 'mcp-server' : 'https://example.com/mcp'"
              />
            </UFormField>
            <UFormField
              v-if="transport === 'stdio'"
              label="Args"
            >
              <UTextarea
                v-model="argsText"
                :rows="2"
                class="w-full"
                placeholder="--root&#10;/path/to/project"
              />
            </UFormField>
            <UFormField label="Description">
              <UTextarea
                v-model="description"
                :rows="2"
                class="w-full"
              />
            </UFormField>
            <UFormField
              v-if="transport === 'stdio'"
              label="Environment"
            >
              <UTextarea
                v-model="envText"
                :rows="2"
                class="w-full"
                placeholder="API_KEY=value"
              />
            </UFormField>
            <UFormField
              v-else
              label="Headers"
            >
              <UTextarea
                v-model="headersText"
                :rows="2"
                class="w-full"
                placeholder="Authorization=Bearer token"
              />
            </UFormField>
            <div class="grid gap-2 rounded-md border border-default/70 px-2.5 py-2">
              <div class="flex items-center justify-between gap-3">
                <span class="text-sm text-highlighted">Enabled</span>
                <USwitch
                  v-model="enabled"
                  size="sm"
                />
              </div>
              <div class="flex items-center justify-between gap-3">
                <span class="text-sm text-highlighted">Trusted</span>
                <USwitch
                  v-model="trusted"
                  size="sm"
                />
              </div>
            </div>
            <UButton
              block
              icon="i-ph-plus"
              size="sm"
              :loading="creating"
              :disabled="!name.trim() || !commandOrUrl.trim() || creating"
              @click="createServer"
            >
              Add Server
            </UButton>
          </div>
        </template>
      </UPopover>
    </div>

    <div class="grid min-w-0 content-start gap-1.5">
      <div
        v-if="!pending && !(servers ?? []).length"
        class="rounded-md border border-dashed border-default px-3 py-6 text-sm text-muted"
      >
        No MCP servers configured.
      </div>
      <div
        v-for="server in servers"
        :key="server.id"
        class="grid gap-2 rounded-md bg-elevated/45 px-3 py-2.5 ring ring-default"
      >
        <div class="flex min-w-0 items-center gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex min-w-0 flex-wrap items-center gap-2">
              <div class="truncate text-sm font-semibold text-highlighted">
                {{ server.name }}
              </div>
              <UBadge
                size="sm"
                variant="soft"
                color="neutral"
              >
                {{ server.transport }}
              </UBadge>
              <UBadge
                v-if="server.trusted"
                size="sm"
                variant="soft"
                color="warning"
              >
                trusted
              </UBadge>
            </div>
            <div class="truncate text-xs text-muted">
              {{ serverEndpoint(server) }}
            </div>
            <div
              v-if="server.description"
              class="mt-0.5 truncate text-xs text-muted"
            >
              {{ server.description }}
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-3">
            <div class="flex items-center gap-1.5">
              <span class="text-xs text-muted">Enabled</span>
              <USwitch
                :model-value="server.enabled"
                size="sm"
                aria-label="Enable MCP server"
                :disabled="updatingServerId === server.id"
                @update:model-value="patchServer(server, { enabled: Boolean($event) })"
              />
            </div>
            <div class="flex items-center gap-1.5">
              <span class="text-xs text-muted">Trusted</span>
              <USwitch
                :model-value="server.trusted"
                size="sm"
                aria-label="Trust MCP server"
                :disabled="updatingServerId === server.id"
                @update:model-value="patchServer(server, { trusted: Boolean($event) })"
              />
            </div>
            <UButton
              icon="i-ph-trash"
              color="error"
              variant="ghost"
              size="xs"
              :loading="deletingServerId === server.id"
              @click="deleteServer(server)"
            />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
