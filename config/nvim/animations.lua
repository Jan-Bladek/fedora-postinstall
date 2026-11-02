-- Use LazyVim's existing Snacks UI; nano remains EDITOR/VISUAL.
return {
  { "folke/snacks.nvim", opts = {
    animate = { enabled = true, duration = 20, easing = "outQuad", fps = 60 },
    scroll = { enabled = true, animate = { duration = { step = 15, total = 150 }, easing = "linear" } },
    indent = { enabled = true, animate = { enabled = true, duration = { step = 15, total = 150 } } },
  } },
}
