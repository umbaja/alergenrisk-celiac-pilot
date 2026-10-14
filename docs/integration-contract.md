# Integračný kontrakt v1

Pilot nemení existujúce používateľské rozhranie. Produkčný adaptér má prijať odvodené genetické príznaky a vrátiť jednotný výsledok.

## Vstup

```json
{
  "schema_version": "1.0",
  "model_id": "alergenrisk-celiac-pilot-v1",
  "sample_reference": "lokálny-pseudonym",
  "features": {
    "obs_rs4143332": 2,
    "quality_rs4143332": 1.0
  },
  "chip_profile": "23andme_like"
}
```

## Výstup

```json
{
  "schema_version": "1.0",
  "model_id": "alergenrisk-celiac-pilot-v1",
  "model_version": "0.1.0",
  "classification": "high",
  "class_probabilities": {"low": 0.01, "typical": 0.14, "high": 0.85},
  "high_risk_threshold": 0.13,
  "coverage": {"direct": 31, "proxy": 11, "population": 8},
  "interpretation": "algorithmic-fidelity research output",
  "clinical_validation": false
}
```

Hodnota prahu `0.13` patrí k artefaktu `structured.npz` vytvorenému referenčným behom so seed `20261014`. Každá nová verzia modelu musí exportovať vlastný prah zvolený výhradne na validačnej množine; klient ho nesmie preberať natvrdo bez kontroly verzie modelu.

## Ochrana údajov

Preferované je lokálne spustenie modelu alebo odovzdanie iba odvodených príznakov. Surový genotyp sa nemá prenášať do obrazovej platformy bez samostatného právneho základu, informovaného súhlasu a bezpečnostnej analýzy.

