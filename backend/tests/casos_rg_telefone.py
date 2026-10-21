"""Casos de RG e telefone para medir a detecção (PBI E3-09, issue #82).

Cada caso é um trecho de documento. `esperado` é o valor que precisa ser
detectado como aquele tipo; `None` quer dizer que o trecho NÃO contém um
dado daquele tipo, e qualquer detecção dele é falso positivo.

Os trechos imitam o que aparece nos documentos de demonstração (ver
scripts/gerar_pdf_exemplo.py e na demonstração do PI-III) e em documentos reais: números de processo,
protocolos, CEP, valores e códigos ao lado dos dados pessoais.
"""

RG = [
    # verdadeiros: formato com pontos, ou precedido de rótulo
    ("RG: 12.345.678-9", "12.345.678-9"),
    ("portador do RG 4.567.890 SSP/DF", "4.567.890"),
    ("Registro Geral: 23.456.789-X", "23.456.789-X"),
    ("Identidade nº 12345678", "12345678"),
    ("RG n° 9876543-2", "9876543-2"),
    ("R.G.: 45678901", "45678901"),
    ("carteira de identidade 1.234.567", "1.234.567"),
    # fim de frase e enumeração (#174): ponto ou vírgula logo depois do número
    ("portadora do RG 12.345.678-9.", "12.345.678-9"),
    ("RG 12.345.678-9, CPF 529.982.247-25", "12.345.678-9"),
    ("Identidade nº 12345678.", "12345678"),
    ("R.G.: 45678901, expedido pela SSP/DF", "45678901"),
    # formatos usados aqui (scripts/gerar_pdf_exemplo.py): órgão emissor depois do número
    ("CPF: 123.456.789-09   RG: 12345678-SSP", "12345678"),
    ("RG: 12.345.678-9/SSP", "12.345.678-9"),
    # falsos: números de 7 a 10 dígitos sem rótulo nem pontuação de RG
    ("Processo: 0001234-56.2026.8.07.0001", None),
    ("Protocolo 20261234", None),
    ("Pedido 1234567 registrado", None),
    ("CEP 70040900", None),
    ("Valor total: 12345678", None),
    ("Valor da causa: R$ 1.234.567,00", None),
    ("Matricula 123456789", None),
    ("CNPJ 11.222.333/0001-81", None),
    ("CPF 529.982.247-25", None),
    ("Telefone 61 99876-5432", None),
    ("ORGANIZACAO 1234567", None),
    # ponto ou vírgula seguidos de dígito continuam o número: não é RG
    ("Indice 12.345.678.9", None),
    ("Saldo R$ 12.345.678,90", None),
]

TELEFONE = [
    # verdadeiros: com DDD, com ou sem o 9, com separador
    ("Telefone: 61 99876-5432", "61 99876-5432"),
    ("Contato (61) 99876-5432", "(61) 99876-5432"),
    ("Tel (21)2345-6789", "(21)2345-6789"),
    ("Fixo: 61 3456-7890", "61 3456-7890"),
    ("Celular (11) 987654321", "(11) 987654321"),
    ("WhatsApp 6199876-5432", "6199876-5432"),
    # fim de frase e enumeração (#174)
    ("o e-mail e o telefone (61) 99876-5432.", "(61) 99876-5432"),
    ("ligue 61 3456-7890, das 8h às 18h", "61 3456-7890"),
    ("Contato: (61) 99876-5432; e-mail no rodapé", "(61) 99876-5432"),
    ("WhatsApp 6199876-5432.", "6199876-5432"),
    # formatos aceitos por PHONE_PATTERN: +55 e hífen depois do DDD
    ("+55 61 99876-5432", "+55 61 99876-5432"),
    ("Tel 61-99876-5432.", "61-99876-5432"),
    # falsos: sem DDD, ou números longos sem separador de telefone
    ("Ramal 99876-5432", None),
    ("Recado: 3456-7890", None),
    ("Protocolo 2026000123", None),
    ("Codigo de barras 12345678901234", None),
    ("Processo: 0001234-56.2026.8.07.0001", None),
    ("CPF 529.982.247-25", None),
    ("CNPJ 11.222.333/0001-81", None),
    ("Pedido 1234567890", None),
    # ponto ou vírgula seguidos de dígito continuam o número: não é telefone
    ("Codigo 61 3456-7890.12", None),
    ("Lote 61 3456-7890,5 kg", None),
]
