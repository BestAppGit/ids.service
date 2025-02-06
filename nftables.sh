#!/bin/bash

#CRIANDO CHAINS
nft add table ip filter
nft add chain ip filter INPUT { type filter hook input priority 0 \; policy accept \; }
nft add chain ip filter FORWARD { type filter hook forward priority 0 \; policy accept \; }
nft add chain ip filter OUTPUT { type filter hook output priority 0 \; policy accept \; }

nft add table ip6 filter
nft add chain ip6 filter INPUT { type filter hook input priority 0 \; policy accept \; }
nft add chain ip6 filter FORWARD { type filter hook forward priority 0 \; policy accept \; }
nft add chain ip6 filter OUTPUT { type filter hook output priority 0 \; policy accept \; }

#CRIANDO O CONJUNTO WHITELIST, IDS_BAN E BOTS_BAN:
nft add set ip filter whitelist { type ipv4_addr\; flags interval\; }
nft add set ip filter ids_ban { type ipv4_addr\; flags interval, timeout\; timeout 24h\; }
nft add set ip filter bots_ban { type ipv4_addr\; flags interval, timeout\; timeout 48h\; }

#nft add set ip6 filter whitelist { type ipv6_addr\; flags interval\; }
#nft add set ip6 filter ids_ban { type ipv6_addr\; flags timeout\; timeout 12h\; }
#nft add set ip6 filter bots_ban { type ipv6_addr\; flags timeout\; timeout 24h\; }

#CRIANDO REGRA PARA OS CONJUNTOS:
nft insert rule ip filter INPUT ip saddr @bots_ban drop
nft insert rule ip filter INPUT ip saddr @ids_ban drop
nft insert rule ip filter INPUT ip saddr @ntopng_ban drop
nft insert rule ip filter INPUT ip saddr @whitelist accept

#nft insert rule ip6 filter INPUT ip6 saddr @bots_ban drop
#nft insert rule ip6 filter INPUT ip6 saddr @ids_ban drop
#nft insert rule ip6 filter INPUT ip6 saddr @whitelist accept

#LIMITANDO CONEXÕES ATIVAS
nft add rule ip filter INPUT tcp dport { 80, 443 } meter conn_meter { ip saddr ct count over 10 } reject
#nft add rule ip6 filter INPUT tcp dport { 80, 443 } meter conn_meter { ip6 saddr ct count over 20 } counter reject
