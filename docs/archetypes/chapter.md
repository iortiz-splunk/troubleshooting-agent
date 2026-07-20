---
title: "{{ replace .Name "-" " " | title }}"
description: ""
weight: {{ replaceRE "[^0-9]" "" .File.Dir | default 99 }}
duration: ""
author: "Workshop Team"
chapter: {{ replaceRE "[^0-9]" "" .File.Dir | default 1 }}
draft: true
---
