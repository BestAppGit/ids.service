#!/bin/bash

#CRIANDO CHAIN INPUT
nft add chain ip filter INPUT

#CRIANDO O CONJUNTO WHITELIST, IDS_BAN E BOTS_BAN:
nft add set ip filter whitelist { type ipv4_addr\; flags interval\; }
nft add set ip filter ids_ban { type ipv4_addr\; flags timeout\; timeout 12h\; }
nft add set ip filter bots_ban { type ipv4_addr\; flags timeout\; timeout 24h\; }

#nft add set ip6 filter whitelist { type ipv6_addr\; flags interval\; }
#nft add set ip6 filter ids_ban { type ipv6_addr\; flags timeout\; timeout 12h\; }
#nft add set ip6 filter bots_ban { type ipv6_addr\; flags timeout\; timeout 24h\; }

#CRIANDO REGRA PARA OS CONJUNTOS:
nft insert rule ip filter INPUT ip saddr @bots_ban drop
nft insert rule ip filter INPUT ip saddr @ids_ban drop
nft insert rule ip filter INPUT ip saddr @whitelist accept

#nft insert rule ip6 filter INPUT ip6 saddr @bots_ban drop
#nft insert rule ip6 filter INPUT ip6 saddr @ids_ban drop
#nft insert rule ip6 filter INPUT ip6 saddr @whitelist accept

#LIMITANDO CONEXÕES ATIVAS
nft add rule ip filter INPUT tcp dport { 80, 443 } meter conn_meter { ip saddr ct count over 20 } reject
#nft add rule ip6 filter INPUT tcp dport { 80, 443 } meter conn_meter { ip6 saddr ct count over 20 } counter reject

#LIMITANDO NOVAS CONEXÕES POR SEGUNDO
nft add rule ip filter INPUT tcp dport {80, 443} ct state new limit rate 5/second accept
nft add rule ip filter INPUT tcp dport { 80, 443 } ct state new reject
#nft add rule ip6 filter INPUT tcp dport {80, 443} ct state new limit rate 2/second counter accept