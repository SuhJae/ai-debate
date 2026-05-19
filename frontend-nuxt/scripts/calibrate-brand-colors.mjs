import colors from 'tailwindcss/colors'

const shades = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]

function parseOklch(value) {
  const [, l, c, h] = value.match(/oklch\(([\d.]+)%\s+([\d.]+)\s+([\d.]+)/) || []
  return {
    l: Number(l),
    c: Number(c),
    h: Number(h)
  }
}

function hexToRgb(hex) {
  const raw = hex.replace('#', '')
  return [0, 2, 4].map(index => Number.parseInt(raw.slice(index, index + 2), 16) / 255)
}

function srgbToLinear(value) {
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
}

function linearToSrgb(value) {
  return value <= 0.0031308 ? 12.92 * value : 1.055 * value ** (1 / 2.4) - 0.055
}

function hexToOklch(hex) {
  const [red, green, blue] = hexToRgb(hex).map(srgbToLinear)
  const l = 0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue
  const m = 0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue
  const s = 0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue
  const l_ = Math.cbrt(l)
  const m_ = Math.cbrt(m)
  const s_ = Math.cbrt(s)
  const lab = {
    l: 0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_,
    a: 1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_,
    b: 0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_
  }
  const h = (Math.atan2(lab.b, lab.a) * 180 / Math.PI + 360) % 360

  return {
    l: lab.l * 100,
    c: Math.sqrt(lab.a ** 2 + lab.b ** 2),
    h
  }
}

function oklchToRgb({ l, c, h }) {
  const hue = h * Math.PI / 180
  const lab = {
    l: l / 100,
    a: Math.cos(hue) * c,
    b: Math.sin(hue) * c
  }
  const l_ = lab.l + 0.3963377774 * lab.a + 0.2158037573 * lab.b
  const m_ = lab.l - 0.1055613458 * lab.a - 0.0638541728 * lab.b
  const s_ = lab.l - 0.0894841775 * lab.a - 1.291485548 * lab.b
  const l3 = l_ ** 3
  const m3 = m_ ** 3
  const s3 = s_ ** 3
  const red = 4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3
  const green = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3
  const blue = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.707614701 * s3

  return [red, green, blue].map(linearToSrgb)
}

function inGamut(rgb) {
  return rgb.every(value => value >= 0 && value <= 1)
}

function toHexChannel(value) {
  return Math.round(Math.min(1, Math.max(0, value)) * 255).toString(16).padStart(2, '0')
}

function oklchToHex(oklch) {
  let candidate = oklch

  if (!inGamut(oklchToRgb(candidate))) {
    let low = 0
    let high = oklch.c

    for (let i = 0; i < 24; i++) {
      const mid = (low + high) / 2
      candidate = { ...oklch, c: mid }

      if (inGamut(oklchToRgb(candidate))) low = mid
      else high = mid
    }

    candidate = { ...oklch, c: low }
  }

  return `#${oklchToRgb(candidate).map(toHexChannel).join('')}`
}

function referenceScale(name) {
  return Object.fromEntries(shades.map(shade => [shade, parseOklch(colors[name][shade])]))
}

function buildHueScale(start, end) {
  return Object.fromEntries(shades.map((shade, index) => {
    const t = index / (shades.length - 1)
    return [shade, start + (end - start) * t]
  }))
}

function buildPalette({ reference, hue, hueScale, chromaScale, anchors = {} }) {
  const ref = referenceScale(reference)

  return Object.fromEntries(shades.map((shade) => {
    const referenceColor = ref[shade]
    const hex = anchors[shade] || oklchToHex({
      l: referenceColor.l,
      c: referenceColor.c * chromaScale,
      h: hueScale?.[shade] ?? hue
    })

    return [shade, {
      hex,
      oklch: hexToOklch(hex),
      target: referenceColor
    }]
  }))
}

const anchors = {
  joseon: hexToOklch('#b82229'),
  brass: hexToOklch('#b8842e'),
  celadon: hexToOklch('#347c7f'),
  pine: hexToOklch('#3d8a61')
}

const palettes = {
  joseon: buildPalette({
    reference: 'red',
    hue: anchors.joseon.h,
    chromaScale: anchors.joseon.c / parseOklch(colors.red[700]).c,
    anchors: { 700: '#b82229' }
  }),
  ink: buildPalette({
    reference: 'stone',
    hueScale: buildHueScale(84, 270),
    chromaScale: 1.8
  }),
  brass: buildPalette({
    reference: 'amber',
    hue: anchors.brass.h,
    chromaScale: anchors.brass.c / parseOklch(colors.amber[600]).c
  }),
  celadon: buildPalette({
    reference: 'teal',
    hue: anchors.celadon.h,
    chromaScale: anchors.celadon.c / parseOklch(colors.teal[600]).c
  }),
  pine: buildPalette({
    reference: 'emerald',
    hue: anchors.pine.h,
    chromaScale: anchors.pine.c / parseOklch(colors.emerald[600]).c
  })
}

for (const [name, palette] of Object.entries(palettes)) {
  console.log(`  /* ${name}: Tailwind ${name === 'ink' ? 'stone' : name === 'joseon' ? 'red' : name === 'brass' ? 'amber' : name === 'pine' ? 'emerald' : 'teal'} OKLCH lightness curve */`)
  for (const shade of shades) {
    console.log(`  --color-${name}-${shade}: ${palette[shade].hex}; /* L ${palette[shade].oklch.l.toFixed(1)} target ${palette[shade].target.l.toFixed(1)} */`)
  }
  console.log('')
}
