import type { DebateState } from '~/types/debate-state'

export function createDemoDebateState(): DebateState {
  return {
    id: 'demo',
    title: 'Demo Debate',
    user_prompt: 'Choose a backend shape. Keep evidence and consensus visible.',
    phase: 'consensus_reached',
    mode: 'engineering_debate',
    created_at: '2026-05-11T00:00:00.000Z',
    updated_at: '2026-05-11T00:08:00.000Z',
    tool_mode: 'probe',
    allow_web_evidence: true,
    agents: {
      codex: {
        provider: 'codex',
        display_name: 'Codex',
        model: 'gpt-5.4',
        write_thesis: true,
        debate_style: 'normal',
        technical_preference: 'conservative',
        additional_note: '',
        session_id: 'demo-codex',
        status: 'done',
        last_error: null
      },
      gemini: {
        provider: 'gemini',
        display_name: 'Gemini',
        model: 'gemini-2.5-pro',
        write_thesis: true,
        debate_style: 'collaborative',
        technical_preference: 'innovative',
        additional_note: '',
        session_id: 'demo-gemini',
        status: 'done',
        last_error: null
      },
      judge: {
        provider: 'claude',
        display_name: 'Judge',
        model: 'claude-sonnet-4-6',
        write_thesis: false,
        debate_style: 'neutral',
        technical_preference: 'neutral',
        additional_note: '',
        session_id: 'demo-judge',
        status: 'done',
        last_error: null
      }
    },
    turn_order: ['codex', 'gemini', 'judge'],
    next_agent: 'codex',
    auto_mode: true,
    pause_after_this: false,
    send_after_this: null,
    user_messages: [],
    theses: {
      codex: {
        agent: 'codex',
        position: 'Use FastAPI first.',
        decision: 'FastAPI',
        action_plan: ['Expose typed routes', 'Stream debate events'],
        risks: ['Model CLI failures'],
        success_criteria: ['OpenAPI loads', 'turn endpoint streams'],
        evidence_refs: ['file-routes'],
        artifact_path: 'theses/codex.md'
      },
      gemini: {
        agent: 'gemini',
        position: 'Agree, but prove command and docs paths.',
        decision: 'FastAPI with probes',
        action_plan: ['Run read-only checks'],
        risks: ['Bad workspace cwd'],
        success_criteria: ['Evidence cards render'],
        evidence_refs: ['cmd-ok', 'web-doc'],
        artifact_path: 'theses/gemini.md'
      }
    },
    rounds: [
      {
        index: 1,
        agent: 'codex',
        discussion: 'I like @gemini checking docs. Here is a short code block that should not highlight mentions:\n\n```ts\nconst route = `/debate/${id}`\n// @gemini stays plain in code\n```',
        agreements: ['Use route-specific pages'],
        disagreements: ['None yet'],
        updated_position: 'Keep FastAPI.',
        proposed_next_action: 'Ask for consensus.',
        evidence_refs: ['file-routes', 'cmd-ok'],
        consensus_action: {
          type: 'consensus_action',
          action: 'propose',
          final_writer: 'codex',
          consensus_summary: 'FastAPI route plus rich transcript.'
        },
        consensus_signal: null,
        artifact_path: 'rounds/round-001-codex.md'
      },
      {
        index: 2,
        agent: 'gemini',
        discussion: 'I accept @codex and add web evidence.',
        agreements: ['Transcript should show markdown and tools'],
        disagreements: ['Need failed probe display too'],
        updated_position: 'Accept with evidence.',
        proposed_next_action: 'Show failed command card.',
        evidence_refs: ['web-doc', 'cmd-fail'],
        consensus_action: {
          type: 'consensus_action',
          action: 'accept',
          proposal_id: 'consensus-001-codex'
        },
        consensus_signal: null,
        artifact_path: 'rounds/round-002-gemini.md'
      },
      {
        index: 3,
        agent: 'judge',
        discussion: 'I reject an older draft because it hid the shared source.',
        agreements: ['Evidence must be shared'],
        disagreements: ['Do not hide shared-source proposals'],
        updated_position: 'Require a shared-source card.',
        proposed_next_action: 'Add shared-source proposal.',
        evidence_refs: ['mcp-docs'],
        consensus_action: {
          type: 'consensus_action',
          action: 'reject',
          proposal_id: 'consensus-old',
          reason: 'Missing MCP evidence.'
        },
        consensus_signal: null,
        artifact_path: 'rounds/round-003-judge.md'
      },
      {
        index: 4,
        agent: 'judge',
        discussion: 'I withdraw the old objection after the shared source is visible.',
        agreements: ['All required cards render'],
        disagreements: [],
        updated_position: 'Accept current flow.',
        proposed_next_action: 'Draft final.',
        evidence_refs: [],
        consensus_action: {
          type: 'consensus_action',
          action: 'withdraw',
          proposal_id: 'consensus-old'
        },
        consensus_signal: null,
        artifact_path: 'rounds/round-004-judge.md'
      }
    ],
    shared_evidence: [
      {
        id: 'file-routes',
        agent: 'codex',
        kind: 'file_ref',
        summary: 'Route schema exists.',
        source_type: 'file',
        source_id: 'app/api/routes.py',
        path: 'app/api/routes.py',
        line_start: 130,
        line_end: 156,
        excerpt: 'GET /api/debates/{debate_id}',
        created_at: '2026-05-11T00:01:00.000Z'
      },
      {
        id: 'cmd-ok',
        agent: 'gemini',
        kind: 'command_result',
        summary: 'Backend test passed.',
        source_type: 'command',
        source_id: 'pytest',
        command: 'pytest tests/backend/test_api_llm_providers.py',
        cwd: '/workspace',
        exit_code: 0,
        output_summary: '1 passed',
        created_at: '2026-05-11T00:02:00.000Z'
      },
      {
        id: 'cmd-fail',
        agent: 'gemini',
        kind: 'command_result',
        summary: 'Probe failed.',
        source_type: 'command',
        source_id: 'pnpm',
        command: 'pnpm missing-script',
        cwd: '/workspace',
        exit_code: 1,
        output_summary: 'ERR_PNPM_NO_SCRIPT',
        created_at: '2026-05-11T00:03:00.000Z'
      },
      {
        id: 'web-doc',
        agent: 'gemini',
        kind: 'web_ref',
        summary: 'FastAPI docs reference.',
        source_type: 'web',
        source_id: 'fastapi-docs',
        url: 'https://fastapi.tiangolo.com/',
        title: 'FastAPI docs',
        query: 'FastAPI OpenAPI docs',
        snippet: 'FastAPI generates OpenAPI.',
        created_at: '2026-05-11T00:04:00.000Z'
      },
      {
        id: 'mcp-docs',
        agent: 'judge',
        kind: 'mcp_ref',
        summary: 'Shared docs source.',
        source_type: 'mcp',
        source_id: 'docs.lookup',
        excerpt: 'Shared source accepted for docs.',
        mcp_server: 'docs',
        mcp_tool: 'lookup',
        created_at: '2026-05-11T00:05:00.000Z'
      }
    ],
    consensus_proposals: [
      {
        id: 'consensus-001-codex',
        proposer: 'codex',
        final_writer: 'codex',
        consensus_summary: 'FastAPI route plus rich transcript.',
        status: 'accepted',
        accepted_by: ['codex', 'gemini', 'judge'],
        rejected_by: {},
        created_at: '2026-05-11T00:06:00.000Z',
        updated_at: '2026-05-11T00:07:00.000Z'
      }
    ],
    consensus: {
      final_writer: 'codex',
      consensus_summary: 'FastAPI route plus rich transcript.',
      agreed_by: ['codex', 'gemini', 'judge'],
      forced_by_user: false
    },
    final_document: {
      draft_version: 1,
      draft_path: 'final/draft.md',
      final_path: null,
      accepted_by: ['gemini', 'judge'],
      drafts: [
        {
          draft_version: 1,
          draft_path: 'final/draft.md',
          created_at: '2026-05-11T00:08:00.000Z',
          status: 'drafted',
          accepted_by: ['gemini', 'judge'],
          reviews: {
            gemini: { status: 'accepted' },
            judge: { status: 'accepted' }
          }
        }
      ]
    },
    reviews: {
      gemini: { status: 'accepted' },
      judge: { status: 'accepted' }
    },
    mcp_registry: [
      {
        id: 'mcp-docs',
        name: 'Docs Source',
        description: 'Shared documentation lookup.',
        transport: 'stdio',
        command_or_url: 'docs-mcp',
        args: ['serve'],
        env: {},
        headers: {},
        trusted: true,
        proposed_by: 'judge',
        status: 'approved',
        created_at: '2026-05-11T00:05:30.000Z'
      }
    ]
  }
}
