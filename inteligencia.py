
from datetime import datetime

class CirculaCore:
    """
    CIRCULA CORE
    Sistema especialista de classificação de embalagens.

    Protótipo educacional baseado em regras.
    """

    MATERIAIS = {
        "papel": {
            "nome": "Papel e Papelão",
            "cor": "Azul",
            "armazenamento": (
                "Manter seco, separado e protegido da chuva."
            ),
            "destinacao": (
                "Cooperativa ou recicladora de papel."
            )
        },
        "plastico": {
            "nome": "Plástico",
            "cor": "Vermelho",
            "armazenamento": (
                "Utilizar recipiente identificado e adequado."
            ),
            "destinacao": (
                "Cooperativa ou recicladora de plástico."
            )
        },
        "vidro": {
            "nome": "Vidro",
            "cor": "Verde",
            "armazenamento": (
                "Acondicionar em recipiente resistente; "
                "proteger contra cortes e quebras."
            ),
            "destinacao": (
                "Recicladora de vidro."
            )
        },
        "metal": {
            "nome": "Metal",
            "cor": "Amarelo",
            "armazenamento": (
                "Armazenar em recipiente identificado, "
                "evitando pontas cortantes expostas."
            ),
            "destinacao": (
                "Recicladora de metais."
            )
        }
    }

    CATALOGO = {
        "PAP001": {
            "material": "papel",
            "contaminacao": "nao",
            "descricao": "Caixa de papelão limpa"
        },
        "PLA001": {
            "material": "plastico",
            "contaminacao": "nao",
            "descricao": "Garrafa PET limpa"
        },
        "VID001": {
            "material": "vidro",
            "contaminacao": "nao",
            "descricao": "Garrafa de vidro limpa"
        },
        "MET001": {
            "material": "metal",
            "contaminacao": "nao",
            "descricao": "Lata metálica limpa"
        },
        "QUI001": {
            "material": "plastico",
            "contaminacao": "sim",
            "descricao": "Galão com resíduo químico"
        }
    }

    @classmethod
    def consultar_codigo(cls, codigo):
        codigo = str(codigo).strip().upper()
        embalagem = cls.CATALOGO.get(codigo)

        if embalagem is None:
            return None

        return {
            "codigo": codigo,
            **embalagem
        }

    @classmethod
    def analisar(cls, dados):
        if not isinstance(dados, dict):
            raise ValueError("Dados inválidos.")

        codigo = str(
            dados.get("codigo", "MANUAL")
        ).strip().upper()[:50] or "MANUAL"

        material = str(
            dados.get("material", "")
        ).strip().lower()

        contaminacao = str(
            dados.get("contaminacao", "incerta")
        ).strip().lower()

        descricao = str(
            dados.get("descricao", "")
        ).strip()[:300]

        try:
            peso = float(dados.get("peso", 0))
        except (TypeError, ValueError):
            raise ValueError("Peso inválido.")

        import math

        if not math.isfinite(peso) or not 0 < peso <= 100000:
            raise ValueError(
                "O peso deve estar entre 0 e 100.000 kg."
            )

        if contaminacao not in ("nao", "sim", "incerta"):
            raise ValueError("Condição de contaminação inválida.")

        # Embalagens cadastradas têm dados conhecidos.
        embalagem = cls.consultar_codigo(codigo)

        if embalagem:
            material = embalagem["material"]

            # Uma embalagem cadastrada como contaminada
            # nunca pode ser liberada como reciclável comum.
            if embalagem["contaminacao"] == "sim":
                contaminacao = "sim"

            if not descricao:
                descricao = embalagem["descricao"]

        regra = cls.MATERIAIS.get(material)

        seguro_para_fluxo_comum = (
            regra is not None
            and contaminacao == "nao"
        )

        if seguro_para_fluxo_comum:
            status = "SEGREGAÇÃO ORIENTADA"
            nivel = "sucesso"
            classificacao = (
                "Material potencialmente reciclável; "
                "periculosidade não certificada."
            )
            coletor = regra["cor"]
            armazenamento = regra["armazenamento"]
            destinacao = regra["destinacao"]

            segregacao = (
                "Separar na origem por tipo de material, "
                "sem misturar com resíduos contaminados."
            )

            movimentacao = (
                "Movimentação interna com carrinho ou "
                "paleteira adequada à carga. Coleta externa "
                "por transportador habilitado quando aplicável."
            )
        else:
            status = (
                "POSSÍVEL CONTAMINAÇÃO PERIGOSA"
                if contaminacao == "sim"
                else "AVALIAÇÃO TÉCNICA NECESSÁRIA"
            )

            nivel = "perigo" if contaminacao == "sim" else "alerta"

            classificacao = (
                "Pendente de avaliação técnica de "
                "periculosidade conforme ABNT NBR 10004."
            )

            coletor = "Não usar a coleta seletiva comum."

            armazenamento = (
                "Manter identificado e segregado, "
                "em local compatível com o risco. "
                "Não manipular sem orientação técnica."
            )

            segregacao = (
                "Não misturar com recicláveis comuns. "
                "Solicitar avaliação do responsável técnico."
            )

            movimentacao = (
                "Definir o transporte após identificação "
                "dos riscos e requisitos legais aplicáveis."
            )

            destinacao = (
                "Definir com responsável técnico e "
                "operador devidamente autorizado."
            )

        alertas = []

        if contaminacao == "sim":
            alertas.append(
                "Possível contaminação: não misturar "
                "com os recicláveis comuns."
            )

        if contaminacao == "incerta":
            alertas.append(
                "Verificar o conteúdo anterior da embalagem."
            )

        if regra is None:
            alertas.append(
                "Material desconhecido: classificação pendente."
            )

        if peso >= 100:
            alertas.append(
                "Carga elevada: verificar capacidade dos "
                "recipientes e equipamentos de movimentação."
            )

        return {
            "codigo": codigo,
            "material": material,
            "material_nome": (
                regra["nome"] if regra else "Desconhecido"
            ),
            "peso": peso,
            "descricao": descricao,
            "contaminacao": contaminacao,
            "status": status,
            "nivel": nivel,
            "classificacao": classificacao,
            "coletor": coletor,
            "segregacao": segregacao,
            "armazenamento": armazenamento,
            "movimentacao": movimentacao,
            "destinacao": destinacao,
            "alertas": alertas,
            "requer_avaliacao": not seguro_para_fluxo_comum,
            "data_analise": datetime.now().isoformat(),
            "observacao": (
                "Diagnóstico preliminar automatizado. "
                "Não substitui classificação técnica, "
                "licenças ou documentação ambiental."
            )
        }
