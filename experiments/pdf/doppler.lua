--[[
  DOPPLER — pandoc filter for the shareable PDF build.

  Three jobs:

  1. Title. Each write-up opens with a level-1 heading. That heading becomes
     the PDF title block, and every remaining heading is lifted one level so
     "## 1. The headline" renders as a \section rather than a \subsection.

  2. Dead links. The write-ups link to sibling files inside the git repository
     (../stage2_confirm/..., ../../experiments/...). Those targets do not exist
     for anyone reading a shared PDF, so the link text stays and the dead
     hyperlink goes. External URLs -- OSF, arXiv -- stay live. The provenance
     appendices are untouched: their link text is already inline code, so the
     file paths survive as code-styled text, which is the content there.

  3. Figure captions. In the markdown, the image alt text is accessibility text
     and the italic paragraph underneath is the visible caption. Rendered
     naively the PDF prints both, near-verbatim. So the italic paragraph
     becomes the figure's caption and the duplicate paragraph is dropped.

  4. Breakable paths. TeX will not break a token like
     `rescore_ev_vs_argmax.md`, so wherever one lands near a line end it runs
     into the margin instead of wrapping -- in body text and, worse, inside the
     narrow columns of the papers' wider tables. Inline code is re-emitted with
     explicit break opportunities after path separators.
]]

-- TeX specials that have to be escaped inside \texttt{}.
local TEX_ESCAPES = {
  ['\\'] = '\\textbackslash{}',
  ['{'] = '\\{',
  ['}'] = '\\}',
  ['$'] = '\\$',
  ['&'] = '\\&',
  ['%'] = '\\%',
  ['#'] = '\\#',
  ['_'] = '\\_',
  ['^'] = '\\^{}',
  ['~'] = '\\textasciitilde{}',
}

-- Characters a file path may be broken after.
local BREAK_AFTER = {
  ['_'] = true, ['/'] = true, ['.'] = true, ['-'] = true, [':'] = true,
}

function Code(el)
  if FORMAT ~= 'latex' or #el.classes > 0 then
    return nil
  end

  local parts = {}
  -- Iterate by UTF-8 character, not by byte.
  for ch in el.text:gmatch('[\0-\127\194-\244][\128-\191]*') do
    parts[#parts + 1] = TEX_ESCAPES[ch] or ch
    if BREAK_AFTER[ch] then
      parts[#parts + 1] = '\\allowbreak{}'
    end
  end

  return pandoc.RawInline('latex', '\\texttt{' .. table.concat(parts) .. '}')
end

local function is_external(target)
  return target:match('^%a[%w+.%-]*://') ~= nil
      or target:match('^mailto:') ~= nil
      or target:match('^#') ~= nil
end

-- Repo-relative link -> its own text, unlinked.
function Link(el)
  if is_external(el.target) then
    return nil
  end
  return el.content
end

-- Figure followed by an italics-only paragraph -> that paragraph is the caption.
function Blocks(blocks)
  local out = pandoc.Blocks({})
  local i = 1
  while i <= #blocks do
    local block = blocks[i]
    local next_block = blocks[i + 1]
    local is_italic_para = next_block ~= nil
      and next_block.t == 'Para'
      and #next_block.content == 1
      and next_block.content[1].t == 'Emph'

    if block.t == 'Figure' and is_italic_para then
      block.caption.long = pandoc.Blocks({
        pandoc.Plain(next_block.content[1].content),
      })
      out:insert(block)
      i = i + 2
    else
      out:insert(block)
      i = i + 1
    end
  end
  return out
end

function Pandoc(doc)
  local blocks = doc.blocks

  if #blocks > 0 and blocks[1].t == 'Header' and blocks[1].level == 1 then
    doc.meta.title = pandoc.MetaInlines(blocks[1].content)
    table.remove(blocks, 1)
  end

  doc.blocks = pandoc.walk_block(pandoc.Div(blocks), {
    Header = function(header)
      if header.level > 1 then
        header.level = header.level - 1
      end
      return header
    end,
  }).content

  return doc
end
