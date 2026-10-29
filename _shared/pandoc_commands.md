# Команды для использования Pandoc

```shell
pandoc pr1.md -o pr1.docx --reference-doc=custom-reference.docx
```   

```shell
pandoc pr3.md -F mermaid-filter --lua-filter ~/university/_shared/gost.lua --reference-doc ~/university/_shared/custom-reference.docx -o pr3.docx
```

