---
title: "{{ replaceRE "^[0-9]+-" "" .Name | replace "-" " " | title }}"
description: ""
weight: {{ with findRE "^[0-9]+" .Name }}{{ index . 0 }}{{ else }}99{{ end }}
navTitle: "{{ replaceRE "^[0-9]+-" "" .Name | replace "-" " " | title }}"
draft: true
---

<!-- Content folders use a numeric prefix matching workshop order (e.g. 7-part2-skills).
     Section pages use chapter-header.html automatically.
     Section headings: use ## Title Case for sections and ### Title Case for subsections —
     Hugo applies the gradient bar template via layouts/_default/_markup/render-heading.html.
     Diagrams: {{< diagram src="images/example.png" alt="..." caption="..." >}}
     Callouts (use notice shortcode — do not use blockquotes for tips):
       {{< notice title="Tip" style="tip" >}} Hint text. {{< /notice >}}
       {{< notice title="Note" style="primary" >}} Important note. {{< /notice >}}
       {{< notice title="..." style="green" >}} Connectivity / success callout. {{< /notice >}}
     Place diagrams outside notice blocks, not inside them.
     Collapsible reference tables: {{< collapse title="Click to expand" >}} markdown table {{< /collapse >}} -->
