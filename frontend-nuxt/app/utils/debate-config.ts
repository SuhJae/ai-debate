import type { AgentColorOption, DebateAgentDraft } from '~/types/debate'

export const agentColorOptions: AgentColorOption[] = [
  { value: 'celadon', label: 'Celadon', swatchClass: 'bg-celadon-600 dark:bg-celadon-400', softClass: 'bg-celadon-50/80 dark:bg-celadon-950/45', textClass: 'text-celadon-700 dark:text-celadon-300', borderClass: 'border-celadon-500/70 dark:border-celadon-400/70', ringClass: 'ring-celadon-600/25 dark:ring-celadon-400/25' },
  { value: 'joseon', label: 'Joseon Red', swatchClass: 'bg-joseon-600 dark:bg-joseon-400', softClass: 'bg-joseon-50/80 dark:bg-joseon-950/45', textClass: 'text-joseon-700 dark:text-joseon-300', borderClass: 'border-joseon-500/70 dark:border-joseon-400/70', ringClass: 'ring-joseon-600/25 dark:ring-joseon-400/25' },
  { value: 'brass', label: 'Brass', swatchClass: 'bg-brass-600 dark:bg-brass-400', softClass: 'bg-brass-50/80 dark:bg-brass-950/45', textClass: 'text-brass-700 dark:text-brass-300', borderClass: 'border-brass-500/70 dark:border-brass-400/70', ringClass: 'ring-brass-600/25 dark:ring-brass-400/25' },
  { value: 'pine', label: 'Pine', swatchClass: 'bg-pine-600 dark:bg-pine-400', softClass: 'bg-pine-50/80 dark:bg-pine-950/45', textClass: 'text-pine-700 dark:text-pine-300', borderClass: 'border-pine-500/70 dark:border-pine-400/70', ringClass: 'ring-pine-600/25 dark:ring-pine-400/25' },
  { value: 'sky', label: 'Sky', swatchClass: 'bg-sky-600 dark:bg-sky-400', softClass: 'bg-sky-50/80 dark:bg-sky-950/45', textClass: 'text-sky-700 dark:text-sky-300', borderClass: 'border-sky-500/70 dark:border-sky-400/70', ringClass: 'ring-sky-600/25 dark:ring-sky-400/25' },
  { value: 'violet', label: 'Violet', swatchClass: 'bg-violet-600 dark:bg-violet-400', softClass: 'bg-violet-50/80 dark:bg-violet-950/45', textClass: 'text-violet-700 dark:text-violet-300', borderClass: 'border-violet-500/70 dark:border-violet-400/70', ringClass: 'ring-violet-600/25 dark:ring-violet-400/25' },
  { value: 'slate', label: 'Slate', swatchClass: 'bg-slate-600 dark:bg-slate-300', softClass: 'bg-slate-100/80 dark:bg-slate-900/60', textClass: 'text-slate-700 dark:text-slate-200', borderClass: 'border-slate-500/70 dark:border-slate-400/70', ringClass: 'ring-slate-600/25 dark:ring-slate-300/25' },
  { value: 'orange', label: 'Orange', swatchClass: 'bg-orange-600 dark:bg-orange-400', softClass: 'bg-orange-50/80 dark:bg-orange-950/45', textClass: 'text-orange-700 dark:text-orange-300', borderClass: 'border-orange-500/70 dark:border-orange-400/70', ringClass: 'ring-orange-600/25 dark:ring-orange-400/25' },
  { value: 'lime', label: 'Lime', swatchClass: 'bg-lime-600 dark:bg-lime-400', softClass: 'bg-lime-50/80 dark:bg-lime-950/45', textClass: 'text-lime-700 dark:text-lime-300', borderClass: 'border-lime-500/70 dark:border-lime-400/70', ringClass: 'ring-lime-600/25 dark:ring-lime-400/25' },
  { value: 'indigo', label: 'Indigo', swatchClass: 'bg-indigo-600 dark:bg-indigo-400', softClass: 'bg-indigo-50/80 dark:bg-indigo-950/45', textClass: 'text-indigo-700 dark:text-indigo-300', borderClass: 'border-indigo-500/70 dark:border-indigo-400/70', ringClass: 'ring-indigo-600/25 dark:ring-indigo-400/25' },
  { value: 'fuchsia', label: 'Fuchsia', swatchClass: 'bg-fuchsia-600 dark:bg-fuchsia-400', softClass: 'bg-fuchsia-50/80 dark:bg-fuchsia-950/45', textClass: 'text-fuchsia-700 dark:text-fuchsia-300', borderClass: 'border-fuchsia-500/70 dark:border-fuchsia-400/70', ringClass: 'ring-fuchsia-600/25 dark:ring-fuchsia-400/25' },
  { value: 'rose', label: 'Rose', swatchClass: 'bg-rose-600 dark:bg-rose-400', softClass: 'bg-rose-50/80 dark:bg-rose-950/45', textClass: 'text-rose-700 dark:text-rose-300', borderClass: 'border-rose-500/70 dark:border-rose-400/70', ringClass: 'ring-rose-600/25 dark:ring-rose-400/25' }
]

export const debateStyleItems = [
  { label: 'Aggressive', value: 'aggressive', description: 'Strong claims; tries to convince other agents.' },
  { label: 'Normal', value: 'normal', description: 'Balanced debate and synthesis.' },
  { label: 'Collaborative', value: 'collaborative', description: 'Builds on others and gives ground when evidence is better.' },
  { label: 'Neutral', value: 'neutral', description: 'Judges, steers, and rectifies missed risks.' },
  { label: 'Politician', value: 'politician', description: 'Factional, combative, and entertainment-first.' }
]

export const technicalPreferenceItems = [
  { label: 'Conservative', value: 'conservative', description: 'Safety-first and battle-tested.' },
  { label: 'Neutral', value: 'neutral', description: 'Balances proven and newer tools.' },
  { label: 'Innovative', value: 'innovative', description: 'Modern designs with managed risk.' },
  { label: 'Frontier', value: 'frontier', description: 'Latest technology with more early-adopter risk.' }
]

export const politicalFactionItems = [
  { label: 'Left', value: 'left', description: 'Public benefit, accountability, access, and vendor skepticism.' },
  { label: 'Right', value: 'right', description: 'Control, cost discipline, speed, ownership, and bureaucracy skepticism.' },
  { label: 'Independent', value: 'independent', description: 'Opportunistic coalition building and tactical distance.' }
]

export function isPoliticalFaction(value: string | undefined) {
  return politicalFactionItems.some(item => item.value === value)
}

export function isTechnicalPreference(value: string | undefined) {
  return technicalPreferenceItems.some(item => item.value === value)
}

export function agentColor(value: string | undefined) {
  return agentColorOptions.find(option => option.value === value) ?? agentColorOptions[0]!
}

export function makeAgent(
  id: string,
  displayName: string,
  provider: string,
  color: string,
  technicalPreference = 'neutral',
  debateStyle = 'normal',
  writeThesis = true
): DebateAgentDraft {
  return {
    id,
    mentionName: id,
    displayName,
    provider,
    model: '',
    color,
    writeThesis,
    debateStyle,
    technicalPreference,
    note: ''
  }
}
