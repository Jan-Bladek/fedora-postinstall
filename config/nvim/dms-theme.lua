-- Use the DMS-generated theme only while DMS is the selected desktop shell.
local config = vim.env.XDG_CONFIG_HOME or (vim.env.HOME .. "/.config")
local file = io.open(config .. "/fedora-postinstall/shell", "r")
local selected = file and file:read("*l") or "noctalia"
if file then file:close() end
if selected ~= "dms" then return {} end

return {
  { "duxlabs-dev/base46", commit = "b3beb806e1a5de9ea883b9968274dd908a50ce94", lazy = true, opts = {} },
  { "LazyVim/LazyVim", opts = {
    colorscheme = function()
      -- First install may precede DMS's first theme generation.
      if vim.fn.filereadable(config .. "/nvim/colors/dms.lua") == 1 then
        vim.cmd.colorscheme("dms")
      else
        vim.cmd.colorscheme("habamax")
      end
    end,
  } },
}
