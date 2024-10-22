# ids.service

Este projeto objetiva atuar como IDS (Sistema de detecção de intrusos), atenuando tanto quanto possível os impactos causados em servidores web,
por acessos maliciosos à sites, e badbots consumindo em sua varredura grande quantidade de recursos do servidor.

O script analisa logs em tempo real e baseado nas regras configuradas, adiciona os ips identificados como maliciosos à sets (conjuntos) do nftables.

O nftables se mostra opção de maior eficiência se comparado a solução "iptables + ipset" por alguns motivos, dentre os quais:
- Código atualizado
- Melhor performance e menor consumo de recursos do servidor
- Trabalha nativamente com sets (conjuntos)
- Suporta nativamente ipv6

Apesar de complexo no começo, após a adaptação, suas regras são mais simplistas e objetivas.

Trabalhamos com 3 arquivos principais, onde:

- ids.py - O script IDS em si
- nftables.conf - Configurações necessárias para o nftables
- ids.service - Cria um serviço para o script, permitindo sua execução constante


---


Sistema base de execução:
- Rocky 8.10 (Green Obsidian)
- Openlitespeed 1.8.1
- aaPanel 7.0.9
