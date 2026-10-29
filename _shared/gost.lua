-- Фильтр для pandoc: правки содержимого, которые нельзя сделать стилями.

-- 1. Убрать горизонтальные линии (--- / *** в markdown)
function HorizontalRule()
  return {}
end

-- 2. Плотные списки: Plain -> Para, чтобы они не использовали стиль
--    "Compact" (он теперь мелкий и только для таблиц)
local function loosen(list)
  for _, item in ipairs(list.content) do
    for i, block in ipairs(item) do
      if block.t == "Plain" then
        item[i] = pandoc.Para(block.content)
      end
    end
  end
  return list
end
function BulletList(l) return loosen(l) end
function OrderedList(l) return loosen(l) end

-- 3. Картинка в отдельном абзаце: стиль "Figure" (по центру, без отступа)
function Para(el)
  if #el.content == 1 and el.content[1].t == "Image" then
    return pandoc.Div({el}, pandoc.Attr("", {}, {["custom-style"] = "Figure"}))
  end
end
