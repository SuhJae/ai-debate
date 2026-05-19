export default defineAppConfig({
  ui: {
    colors: {
      primary: 'celadon',
      secondary: 'brass',
      success: 'pine',
      info: 'celadon',
      warning: 'brass',
      error: 'joseon',
      neutral: 'ink'
    },
    card: {
      slots: {
        root: 'rounded-md overflow-hidden shadow-sm'
      },
      variants: {
        variant: {
          outline: {
            root: 'bg-elevated ring ring-default divide-y divide-default'
          },
          subtle: {
            root: 'bg-elevated ring ring-default divide-y divide-default'
          },
          soft: {
            root: 'bg-muted divide-y divide-default'
          }
        }
      }
    },
    dashboardSidebar: {
      slots: {
        root: 'bg-muted/35 dark:bg-transparent'
      }
    },
    navigationMenu: {
      compoundVariants: [{
        disabled: false,
        active: false,
        variant: 'pill',
        class: {
          link: 'hover:text-highlighted hover:before:bg-accented/70 data-[state=open]:before:bg-accented/70',
          linkLeadingIcon: 'group-hover:text-default group-data-[state=open]:text-default'
        }
      }, {
        variant: 'pill',
        active: true,
        highlight: false,
        class: {
          link: 'before:bg-accented text-highlighted',
          linkLeadingIcon: 'text-highlighted'
        }
      }, {
        variant: 'pill',
        active: true,
        highlight: true,
        disabled: false,
        class: {
          link: 'hover:before:bg-accented/70'
        }
      }]
    },
    button: {
      compoundVariants: [{
        color: 'neutral',
        variant: 'ghost',
        class: 'hover:bg-accented/70 data-[state=open]:bg-accented/70'
      }]
    },
    kbd: {
      variants: {
        variant: {
          soft: 'bg-accented/70'
        }
      }
    },
    modal: {
      variants: {
        fullscreen: {
          false: {
            content: 'w-[calc(100vw-2rem)] max-w-lg rounded-md shadow-lg ring ring-default'
          }
        }
      }
    },
    icons: {
      arrowDown: 'i-ph-arrow-down',
      arrowLeft: 'i-ph-arrow-left',
      arrowRight: 'i-ph-arrow-right',
      arrowUp: 'i-ph-arrow-up',
      caution: 'i-ph-warning-circle',
      check: 'i-ph-check',
      chevronDoubleLeft: 'i-ph-caret-double-left',
      chevronDoubleRight: 'i-ph-caret-double-right',
      chevronDown: 'i-ph-caret-down',
      chevronLeft: 'i-ph-caret-left',
      chevronRight: 'i-ph-caret-right',
      chevronUp: 'i-ph-caret-up',
      close: 'i-ph-x',
      copy: 'i-ph-copy',
      copyCheck: 'i-ph-check-circle',
      dark: 'i-ph-moon',
      drag: 'i-ph-dots-six-vertical',
      ellipsis: 'i-ph-dots-three',
      error: 'i-ph-x-circle',
      external: 'i-ph-arrow-up-right',
      eye: 'i-ph-eye',
      eyeOff: 'i-ph-eye-slash',
      file: 'i-ph-file',
      folder: 'i-ph-folder',
      folderOpen: 'i-ph-folder-open',
      hash: 'i-ph-hash',
      info: 'i-ph-info',
      light: 'i-ph-sun',
      loading: 'i-ph-circle-notch',
      menu: 'i-ph-list',
      minus: 'i-ph-minus',
      panelClose: 'i-ph-caret-left',
      panelOpen: 'i-ph-caret-right',
      plus: 'i-ph-plus',
      reload: 'i-ph-arrow-counter-clockwise',
      search: 'i-ph-magnifying-glass',
      stop: 'i-ph-square',
      success: 'i-ph-check-circle',
      system: 'i-ph-monitor',
      tip: 'i-ph-lightbulb',
      upload: 'i-ph-upload',
      warning: 'i-ph-warning'
    }
  }
})
