# Data research v0.11.2

- Tradera använder kategori-id `293316` för hockey/sportbilder och `293311` för fotboll/sportbilder.
- FlipFynd använder nu kategori-id från varje item-URL som integritetskontroll för sportklassificering.
- Smart crawl är avsiktligt bounded för Streamlit Community Cloud: 12 sidor per sport, med tidigt stopp efter 2 helt kända sidor.
- Aktivt dataset hålls till högst 1 500 annonser per sport. Detta är en prestandaregel, inte en marknads- eller värderingsregel.
