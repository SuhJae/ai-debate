<script setup lang="ts">
useHead({
  title: '브랜드 스와치 | 조선의 공간',
  link: [
    { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
    { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
    {
      rel: 'stylesheet',
      href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Serif+KR:wght@400;500;600;700;900&display=swap'
    },
    {
      rel: 'stylesheet',
      href: 'https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable.css'
    }
  ]
})

const previewEmail = ref('researcher@snu.ac.kr')

const colorScales = [{
  name: 'joseon',
  title: '조선 레드',
  description: '로고 색상 #b82229를 Tailwind식 700 단계에 둔 주 행동색',
  colors: [
    ['50', '#FDF3F2'],
    ['100', '#FCE3E1'],
    ['200', '#FBCCC7'],
    ['300', '#FAA7A0'],
    ['400', '#F5706A'],
    ['500', '#EE4546'],
    ['600', '#DB2731'],
    ['700', '#B82229'],
    ['800', '#962124'],
    ['900', '#7B2323'],
    ['950', '#420F0E']
  ]
}, {
  name: 'ink',
  title: '먹색 / 한지 뉴트럴',
  description: '밝은 화면은 한지, 어두운 화면은 깊은 먹색으로 구성',
  colors: [
    ['50', '#FBFAF9'],
    ['100', '#F5F5F4'],
    ['200', '#E5E6E2'],
    ['300', '#D1D5D0'],
    ['400', '#98A59D'],
    ['500', '#657772'],
    ['600', '#475757'],
    ['700', '#364347'],
    ['800', '#20272B'],
    ['900', '#161A1F'],
    ['950', '#090A0E']
  ]
}, {
  name: 'brass',
  title: '황동 골드',
  description: '오방색의 황색을 현대적으로 낮춘 보조 강조색',
  colors: [
    ['50', '#FFFAF3'],
    ['100', '#FFF0DC'],
    ['200', '#FFE1B7'],
    ['300', '#FFCE87'],
    ['400', '#F5BB63'],
    ['500', '#E1A850'],
    ['600', '#BD8934'],
    ['700', '#976919'],
    ['800', '#785414'],
    ['900', '#624516'],
    ['950', '#372507']
  ]
}, {
  name: 'celadon',
  title: '청자 청록',
  description: '정보, 링크, 선택 상태에 제한적으로 쓰는 차가운 균형색',
  colors: [
    ['50', '#F4FCFC'],
    ['100', '#D9F6F7'],
    ['200', '#B4EEF0'],
    ['300', '#8BE0E4'],
    ['400', '#67C8CD'],
    ['500', '#58B0B3'],
    ['600', '#468D90'],
    ['700', '#3A7173'],
    ['800', '#305A5B'],
    ['900', '#2A4A4C'],
    ['950', '#172C2D']
  ]
}]

const semanticTokens = [{
  role: 'background',
  korean: '배경',
  light: '#FBFAF9',
  dark: '#090A0E',
  usage: '앱 전체 바탕'
}, {
  role: 'surface',
  korean: '표면',
  light: '#FFFDF8',
  dark: '#161A1F',
  usage: '카드, 패널, 폼'
}, {
  role: 'elevated',
  korean: '상승 표면',
  light: '#F5F5F4',
  dark: '#20272B',
  usage: '호버, 드롭다운, 보조 영역'
}, {
  role: 'border',
  korean: '구분선',
  light: '#E5E6E2',
  dark: '#20272B',
  usage: '테두리, 디바이더'
}, {
  role: 'text',
  korean: '본문',
  light: '#171311',
  dark: '#F4F0E7',
  usage: '본문 텍스트'
}, {
  role: 'muted',
  korean: '보조 텍스트',
  light: '#657772',
  dark: '#AEB9B4',
  usage: '설명, 플레이스홀더'
}, {
  role: 'primary',
  korean: '주요 행동',
  light: '#B82229',
  dark: '#DB2731',
  usage: '주 버튼, 활성 상태'
}, {
  role: 'focus',
  korean: '포커스',
  light: '#3A7173',
  dark: '#F5BB63',
  usage: '키보드 포커스 링'
}]

const fontSamples = [{
  name: 'Pretendard Variable',
  role: '한국어 UI / 본문',
  class: 'font-brand-sans',
  sample: '조선시대 문헌 번역을 위한 연구자 작업 공간'
}, {
  name: 'Noto Serif KR',
  role: '한자 / 제목 / 인용',
  class: 'font-brand-serif',
  sample: '朝鮮空間 · 承政院日記 · 實錄'
}, {
  name: 'Inter',
  role: '영문 / 숫자 / 토큰',
  class: 'font-brand-latin',
  sample: '조선투데이 Alpha · AI Translation Queue'
}]
</script>

<template>
  <main class="brand-preview">
    <PublicNavbar>
      <template #actions>
        <UBadge
          color="neutral"
          variant="subtle"
          label="#b82229"
          class="hidden sm:inline-flex"
        />
        <UButton
          to="/sign-in"
          color="neutral"
          variant="ghost"
          label="로그인 화면"
          class="hidden sm:inline-flex"
        />
      </template>
    </PublicNavbar>

    <section class="brand-hero">
      <div class="brand-hero-copy">
        <div>
          <p class="brand-eyebrow">
            조선투데이 아이덴티티
          </p>
          <h1 class="brand-title font-brand-serif">
            <BrandLockup size="hero" />
          </h1>
          <p class="brand-lede">
            로고의 진홍색을 중심으로 먹색, 한지색, 황동, 청자를 절제해 배치한 연구용 AI 제품 브랜드 방향입니다.
          </p>
        </div>

        <div class="brand-font-grid">
          <div
            v-for="sample in fontSamples"
            :key="sample.name"
            class="brand-font-card"
          >
            <p class="brand-meta">
              {{ sample.role }}
            </p>
            <p class="brand-font-sample" :class="sample.class">
              {{ sample.sample }}
            </p>
            <p class="brand-token-label">
              {{ sample.name }}
            </p>
          </div>
        </div>
      </div>

      <div class="brand-preview-panel">
        <div class="mock-light">
          <div class="mock-panel-head mock-light-head">
            <div>
              <p class="mock-title font-brand-serif">
                번역 요청
              </p>
              <p class="mock-muted">
                대학 연구자 인증 후 사용
              </p>
            </div>
            <UIcon name="i-ph-seal-check" class="mock-icon-red" />
          </div>

          <div class="mock-stack">
            <UInput
              v-model="previewEmail"
              icon="i-ph-envelope"
              variant="outline"
              color="neutral"
              class="w-full"
            />
            <div class="mock-callout-light">
              <p>
                환영합니다, Seoul National University 연구자님!
              </p>
              <p>
                승인 대기열 3건 · 예상 처리 2분
              </p>
            </div>
            <div class="mock-actions">
              <UButton
                label="번역 시작"
                icon="i-ph-sparkle"
                color="primary"
              />
              <UButton
                label="초안 저장"
                color="neutral"
                variant="outline"
              />
            </div>
          </div>
        </div>

        <div class="mock-dark">
          <div class="mock-panel-head mock-dark-head">
            <div>
              <p class="mock-title font-brand-serif">
                번역 대화
              </p>
              <p class="mock-muted">
                심각하고 차분한 다크 모드
              </p>
            </div>
            <UIcon name="i-ph-moon-stars" class="mock-icon-brass" />
          </div>
          <div class="mock-stack">
            <div class="mock-bubble">
              원문 문장을 입력하면 단계별 번역 파이프라인을 실행합니다.
            </div>
            <div class="mock-warning">
              인증되지 않은 요청은 프록시에서 차단됩니다.
            </div>
            <div class="mock-actions">
              <UButton
                label="모델 실행"
                icon="i-ph-play"
                color="primary"
              />
              <UButton
                label="로그 보기"
                color="neutral"
                variant="ghost"
              />
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="brand-section">
      <div>
        <h2 class="brand-section-title font-brand-serif">
          팔레트
        </h2>
        <p class="brand-section-copy">
          Tailwind 확장에 넣을 수 있는 4개 색상 램프입니다. 실제 테마 적용 전 색감과 단계 차이를 검토하기 위한 화면입니다.
        </p>
      </div>

      <div class="brand-scale-grid">
        <section
          v-for="scale in colorScales"
          :key="scale.name"
          class="brand-scale-card"
        >
          <div class="brand-scale-head">
            <div>
              <h3 class="brand-scale-title font-brand-serif">
                {{ scale.title }}
              </h3>
              <p class="brand-scale-copy">
                {{ scale.description }}
              </p>
            </div>
            <code class="brand-scale-code">{{ scale.name }}</code>
          </div>

          <div class="brand-swatch-strip">
            <div
              v-for="[step, hex] in scale.colors"
              :key="`${scale.name}-${step}`"
              class="brand-swatch"
              :style="{ backgroundColor: hex }"
            >
              <p
                class="brand-swatch-step"
                :style="{ color: Number(step) >= 500 ? '#FFFFFF' : '#171311' }"
              >
                {{ step }}
              </p>
              <p
                class="brand-swatch-hex"
                :style="{ color: Number(step) >= 500 ? 'rgba(255, 255, 255, 0.8)' : 'rgba(23, 19, 17, 0.7)' }"
              >
                {{ hex }}
              </p>
            </div>
          </div>
        </section>
      </div>
    </section>

    <section class="brand-token-grid">
      <div class="token-panel token-panel-light">
        <h2 class="token-title font-brand-serif">
          라이트 모드 토큰
        </h2>
        <div class="token-list token-list-light">
          <div
            v-for="token in semanticTokens"
            :key="`light-${token.role}`"
            class="token-row"
          >
            <div>
              <p class="token-name">
                {{ token.korean }} <span>/ {{ token.role }}</span>
              </p>
              <p class="token-usage">
                {{ token.usage }}
              </p>
            </div>
            <div class="token-color">
              <span :style="{ backgroundColor: token.light }" />
              <code>{{ token.light }}</code>
            </div>
          </div>
        </div>
      </div>

      <div class="token-panel token-panel-dark">
        <h2 class="token-title font-brand-serif">
          다크 모드 토큰
        </h2>
        <div class="token-list token-list-dark">
          <div
            v-for="token in semanticTokens"
            :key="`dark-${token.role}`"
            class="token-row"
          >
            <div>
              <p class="token-name">
                {{ token.korean }} <span>/ {{ token.role }}</span>
              </p>
              <p class="token-usage">
                {{ token.usage }}
              </p>
            </div>
            <div class="token-color">
              <span :style="{ backgroundColor: token.dark }" />
              <code>{{ token.dark }}</code>
            </div>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.brand-preview {
  min-height: 100vh;
  background: var(--ui-bg);
  color: var(--ui-text);
  font-family: "Pretendard Variable", Pretendard, Inter, "Noto Sans KR", system-ui, sans-serif;
}

.brand-meta,
.brand-section-copy,
.brand-scale-copy,
.brand-token-label {
  color: var(--ui-text-muted);
}

.brand-meta,
.brand-token-label {
  font-size: 0.75rem;
  font-weight: 500;
}

.brand-hero,
.brand-section,
.brand-token-grid {
  width: min(100%, 80rem);
  margin: 0 auto;
  padding-inline: 1rem;
}

.brand-hero {
  display: grid;
  gap: 2rem;
  padding-block: 2.5rem;
}

.brand-hero-copy {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
}

.brand-eyebrow {
  color: var(--ui-primary);
  font-size: 0.875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.22em;
}

.brand-title {
  margin-top: 1rem;
  color: var(--ui-text-highlighted);
  font-size: clamp(3rem, 9vw, 4.5rem);
  font-weight: 900;
  line-height: 1.05;
}

.brand-lede {
  max-width: 42rem;
  margin-top: 1rem;
  color: var(--ui-text-toned);
  font-size: 1rem;
  line-height: 1.75;
}

.brand-font-grid {
  display: grid;
  gap: 0.75rem;
}

.brand-font-card,
.brand-preview-panel,
.brand-scale-card {
  border: 1px solid var(--ui-border);
  background: var(--ui-bg-elevated);
}

.brand-font-card {
  border-radius: 0.375rem;
  padding: 1rem;
}

.brand-font-sample {
  margin-top: 0.75rem;
  color: var(--ui-text-highlighted);
  font-size: 1.25rem;
  font-weight: 600;
}

.brand-token-label {
  margin-top: 0.75rem;
}

.brand-preview-panel {
  border-radius: 0.5rem;
  padding: 1.25rem;
  box-shadow: 0 24px 70px color-mix(in oklab, var(--ui-bg-inverted) 12%, transparent);
}

.mock-light,
.mock-dark {
  border-radius: 0.375rem;
  padding: 1rem;
}

.mock-light {
  background: var(--ui-bg);
  color: var(--ui-text);
}

.mock-dark {
  margin-top: 1rem;
  border: 1px solid var(--ui-border);
  background: var(--ui-bg-muted);
  color: var(--ui-text);
}

.mock-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 0.75rem;
}

.mock-light-head {
  border-bottom: 1px solid var(--ui-border);
}

.mock-dark-head {
  border-bottom: 1px solid var(--ui-border);
}

.mock-title {
  font-size: 1.125rem;
  font-weight: 700;
}

.mock-muted {
  color: var(--ui-text-muted);
  font-size: 0.875rem;
}

.mock-icon-red,
.mock-icon-brass {
  width: 1.75rem;
  height: 1.75rem;
}

.mock-icon-red {
  color: var(--ui-primary);
}

.mock-icon-brass {
  color: var(--ui-warning, var(--ui-primary));
}

.mock-stack {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}

.mock-callout-light,
.mock-bubble,
.mock-warning {
  border-radius: 0.375rem;
  padding: 0.75rem;
  font-size: 0.875rem;
}

.mock-callout-light {
  border: 1px solid var(--ui-border);
  background: var(--ui-bg-muted);
}

.mock-callout-light p:first-child {
  color: var(--ui-text-highlighted);
  font-weight: 500;
}

.mock-callout-light p:last-child {
  margin-top: 0.25rem;
  color: var(--ui-text-muted);
  font-size: 0.75rem;
}

.mock-bubble {
  background: var(--ui-bg-accented);
  color: var(--ui-text-highlighted);
}

.mock-warning {
  border: 1px solid color-mix(in oklab, var(--ui-error, var(--ui-primary)) 46%, var(--ui-border));
  background: color-mix(in oklab, var(--ui-error, var(--ui-primary)) 12%, transparent);
  color: var(--ui-error, var(--ui-primary));
}

.mock-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.mock-actions :deep(button),
.mock-actions :deep(a) {
  border-radius: 0.375rem;
}

.brand-section {
  padding-bottom: 2.5rem;
}

.brand-section-title {
  color: var(--ui-text-highlighted);
  font-size: 1.875rem;
  font-weight: 700;
}

.brand-section-copy {
  margin-top: 0.5rem;
  font-size: 0.875rem;
}

.brand-scale-grid {
  display: grid;
  gap: 1rem;
  margin-top: 1.5rem;
}

.brand-scale-card {
  border-radius: 0.5rem;
  padding: 1rem;
}

.brand-scale-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.brand-scale-title {
  color: var(--ui-text-highlighted);
  font-size: 1.25rem;
  font-weight: 700;
}

.brand-scale-copy {
  margin-top: 0.25rem;
  font-size: 0.875rem;
}

.brand-scale-code {
  border-radius: 0.375rem;
  background: var(--ui-bg-muted);
  color: var(--ui-primary);
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

.brand-swatch-strip {
  display: grid;
  grid-template-columns: repeat(11, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--ui-border);
  border-radius: 0.375rem;
}

.brand-swatch {
  min-height: 6rem;
  padding: 0.5rem;
}

.brand-swatch-step {
  font-size: 0.6875rem;
  font-weight: 700;
}

.brand-swatch-hex {
  margin-top: 2.5rem;
  font-size: 0.625rem;
}

.brand-token-grid {
  display: grid;
  gap: 1.5rem;
  padding-bottom: 3rem;
}

.token-panel {
  border: 1px solid var(--ui-border);
  background: var(--ui-bg-elevated);
  color: var(--ui-text);
  border-radius: 0.5rem;
  padding: 1.25rem;
}

.token-title {
  font-size: 1.5rem;
  font-weight: 700;
}

.token-list {
  margin-top: 1rem;
  overflow: hidden;
  border-radius: 0.375rem;
}

.token-list-light {
  border: 1px solid var(--ui-border);
  background: var(--ui-bg);
}

.token-list-dark {
  border: 1px solid var(--ui-border);
  background: var(--ui-bg);
}

.token-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.75rem;
  padding: 0.75rem;
}

.token-row + .token-row {
  border-top: 1px solid currentcolor;
}

.token-list-light .token-row + .token-row {
  border-color: var(--ui-border);
}

.token-list-dark .token-row + .token-row {
  border-color: var(--ui-border);
}

.token-name {
  font-size: 0.875rem;
  font-weight: 600;
}

.token-name span {
  color: var(--ui-text-muted);
}

.token-usage,
.token-color code {
  color: var(--ui-text-muted);
  font-size: 0.75rem;
}

.token-color {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.token-color span {
  width: 2rem;
  height: 2rem;
  border: 1px solid var(--ui-border);
  border-radius: 0.375rem;
}

.font-brand-sans {
  font-family: "Pretendard Variable", Pretendard, Inter, "Noto Sans KR", system-ui, sans-serif;
}

.font-brand-serif {
  font-family: "Noto Serif KR", "Nanum Myeongjo", "AppleMyungjo", serif;
}

.font-brand-latin {
  font-family: Inter, "Pretendard Variable", system-ui, sans-serif;
}

@media (min-width: 640px) {
  .brand-hero,
  .brand-section,
  .brand-token-grid {
    padding-inline: 1.5rem;
  }

  .brand-font-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .brand-hero,
  .brand-section,
  .brand-token-grid {
    padding-inline: 2rem;
  }

  .brand-hero {
    grid-template-columns: 1.05fr 0.95fr;
  }

  .brand-scale-grid,
  .brand-token-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .brand-swatch-strip {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .brand-swatch {
    min-height: 5rem;
  }

  .token-row {
    grid-template-columns: 1fr;
  }
}
</style>
