"""Casos de CEP, CNH e cartão de pagamento para medir a detecção (PBI E3-10, #83).

Mesmo formato de `casos_rg_telefone.py`: cada caso é um trecho de
documento; `esperado` é o valor que precisa ser detectado como aquele tipo,
e `None` quer dizer que o trecho NÃO contém um dado daquele tipo (qualquer
detecção é falso positivo). Os trechos põem números parecidos lado a lado:
telefone, processo, protocolo, CPF, valores e códigos.

Números usados: as CNHs foram calculadas pelo algoritmo do dígito
verificador e não são de ninguém; os cartões são os números de teste
publicados pelas bandeiras (4111 1111 1111 1111 etc.).
"""

CEP = [
    # verdadeiros: formato 00000-000, 00.000-000, ou rótulo "CEP" com 8 dígitos
    ("CEP 70040-900", "70040-900"),
    ("Brasília/DF, 70.040-900", "70.040-900"),
    ("CEP: 70040900", "70040900"),
    ("CEP nº 01310-100, São Paulo", "01310-100"),
    ("residente na quadra 1, 70040-900.", "70040-900"),
    ("cep 72015030", "72015030"),
    # falsos
    ("Telefone 61 99876-5432", None),
    ("Processo: 0001234-56.2026.8.07.0001", None),
    ("Protocolo 20261234", None),
    ("Valor R$ 12.345,00", None),
    ("CPF 529.982.247-25", None),
    ("Pedido 123456-7890", None),
    ("Código 12345-6789", None),
    ("Matrícula 1234567", None),
]

CNH = [
    # verdadeiros: rótulo de CNH/habilitação + 11 dígitos com DV correto
    ("CNH 02650306461", "02650306461"),
    ("CNH nº 12345678900", "12345678900"),
    ("Carteira Nacional de Habilitação: 04281773660", "04281773660"),
    ("habilitação nº 02650306461, categoria B", "02650306461"),
    ("registro da CNH: 12345678900.", "12345678900"),
    # falsos
    ("CNH 02650306462", None),  # DV errado
    ("CNH 11111111111", None),  # sequência repetida
    ("CPF 529.982.247-25", None),
    ("Protocolo 02650306461", None),  # 11 dígitos válidos, mas sem rótulo de CNH
    ("Telefone 61 99876-5432", None),
    ("CNH categoria B, validade 2030", None),
]

CARTAO = [
    # verdadeiros: grupos de 4 (ou 4-6-5 na Amex) com Luhn válido,
    # ou rótulo de cartão + 13 a 19 dígitos seguidos
    ("Cartão 4111 1111 1111 1111", "4111 1111 1111 1111"),
    ("pago com 5555-5555-5555-4444", "5555-5555-5555-4444"),
    ("Amex 3782 822463 10005", "3782 822463 10005"),
    ("cartão de crédito nº 4111111111111111", "4111111111111111"),
    ("Cartao: 5555555555554444.", "5555555555554444"),
    # falsos
    ("Cartão 4111 1111 1111 1112", None),  # Luhn inválido
    ("Código de barras 4111111111111111", None),  # sem rótulo de cartão
    ("Linha digitável 1234 5678 1234 5678", None),  # Luhn inválido
    ("CNPJ 11.222.333/0001-81", None),
    ("Processo: 0001234-56.2026.8.07.0001", None),
    ("Telefone 61 99876-5432", None),
    ("Cartão 0000 0000 0000 0000", None),  # sequência repetida
]
