# RX Calculator

**Opis**: RX Calculator — kalkulator chłodnego dachu (Streamlit) do szacowania oszczędności energii i kosztów w horyzoncie 20 lat. Usunięto krzywą CO₂ z wykresu kumulacyjnego. Powiększone skale dla ekwiwalentów (drzewa, km, gospodarstwa, żarówki).
**Brandy**: SOLTHERM + BOLIX.

## Struktura
```
rx-calculator/
│── rx_calculator.py     # Główny plik aplikacji (entry point)
│── requirements.txt
│── README.md
│── soltherm.png
│── bolix.png
```

## Uruchomienie lokalne
```bash
pip install -r requirements.txt
streamlit run rx_calculator.py
```

## Deploy (Streamlit Cloud)
- Repozytorium: `rx-calculator` (lub dowolna nazwa)
- Main file path: `rx_calculator.py`
