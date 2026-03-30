from caixa_scanner.sources.caixa_csv import normalize_text
import re
import unicodedata

def clean_city_name(city: str | None) -> str:
    return normalize_text(city or "")

def _alias_variants(name: str) -> set[str]:
    base = normalize_text(name)
    variants = {base}

    extras = {
        base.replace("(", "").replace(")", "").strip(),
        base.replace("-", " ").strip(),
        base.replace("/", " ").strip(),
    }

    variants |= {normalize_text(x) for x in extras if x}

    return {v for v in variants if v}


def _expand_city_neighborhood_scores(raw_map: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    expanded: dict[str, dict[str, float]] = {}

    for city, neighborhoods in raw_map.items():
        city_norm = clean_city_name(city)
        expanded[city_norm] = {}

        for raw_name, score in neighborhoods.items():
            for alias in _alias_variants(raw_name):
                expanded[city_norm][alias] = float(score)

    return expanded

def clean_neighborhood_name(neighborhood: str | None) -> str:
    if not neighborhood:
        return ""

    raw = str(neighborhood).strip()

    # remove parte da cidade/UF quando vier embutida no campo bairro
    # ex.: "PRACA SECA - RIO DE JANEIRO/RJ"
    if " - " in raw:
        raw = raw.split(" - ")[0].strip()

    value = normalize_text(raw)

    # normalizações específicas do CSV
    replacements = {
        "praia do canto": "praia do canto",
        "enseada do sua": "enseada do sua",
        "enseada do suá": "enseada do sua",
        "jardim camburi": "jardim camburi",
        "mata da praia": "mata da praia",
        "mata da praia ": "mata da praia",
        "freguesia": "freguesia jacarepagua",
        "freguesia jacarepagu": "freguesia jacarepagua",
        "freguesia jacarepagua": "freguesia jacarepagua",
        "freguesia (jacarepagua)": "freguesia jacarepagua",
        "bras de pina": "bras de pina",
        "praca seca": "praca seca",
        "vila valqueire": "vila valqueire",
        "rio comprido": "rio comprido",
        "engenho de dentro": "engenho de dentro",
        "engenho novo": "engenho novo",
        "vicente de carvalho": "vicente de carvalho",
        "penha circular": "penha circular",
        "cidade de deus": "cidade de deus",
        "santissimo": "santissimo",
        "honorio gurgel": "honorio gurgel",
        "meier": "meier",
        "turiacu": "turiacu",
        "tomas coelho": "tomas coelho",
    }

    return replacements.get(value, value)

def _alias_variants(name: str) -> set[str]:
    """
    Gera aliases simples e úteis para nomes de bairro.
    A chave final continua normalizada por normalize_text().
    """
    base = normalize_text(name)
    variants = {base}

    replacements = [
        ("-", " "),
        ("'", " "),
        (" d ", " de "),
        (" jd ", " jardim "),
        (" res ", " residencial "),
        (" vl ", " vila "),
        (" n s ", " nossa senhora "),
        (" sta ", " santa "),
        (" sto ", " santo "),
        (" sao ", " são "),
    ]

    for a, b in replacements:
        if a in base:
            variants.add(normalize_text(base.replace(a, b)))
        if b in base:
            variants.add(normalize_text(base.replace(b, a)))

    # remove duplicidade de espaços
    variants = {normalize_text(v) for v in variants if v}

    return variants


def _expand_city_neighborhood_scores(city_map: dict[str, int | float]) -> dict[str, float]:
    expanded: dict[str, float] = {}

    for raw_name, score in city_map.items():
        for alias in _alias_variants(raw_name):
            expanded[alias] = float(score)

    return expanded

CITY_STRUCTURE_SCORES = {
    # Minas Gerais
    "belo horizonte": 94,
    "contagem": 82,
    "betim": 80,
    "nova lima": 88,
    "juiz de fora": 84,
    "uberlandia": 89,
    "uberaba": 82,
    "montes claros": 78,
    "ipatinga": 79,
    "divinopolis": 78,
    "pocos de caldas": 83,
    "poços de caldas": 83,
    "varginha": 79,
    "sete lagoas": 78,
    "lavras": 77,
    "vicosa": 78,
    "viçosa": 78,
    "itabira": 75,
    "governador valadares": 77,
    "pouso alegre": 80,
    "patos de minas": 78,
    "araxa": 77,
    "araxa": 77,
    "conselheiro lafaiete": 75,
    "santa luzia": 72,
    "ribeirao das neves": 65,
    "ribeirão das neves": 65,
    "ibirite": 68,
    "ibirité": 68,
    "sabará": 71,
    "sabara": 71,

    # Outras capitais e cidades fortes, para manter coerência
    "curitiba": 91,
    "porto alegre": 88,
    "florianopolis": 88,
    "brasilia": 93,
    "goiania": 87,
    "salvador": 87,
    "recife": 88,
    "fortaleza": 88,

    "sao paulo": 95,
    "campinas": 88,
    "santos": 87,
    "sao jose dos campos": 86,
    "sorocaba": 84,
    "ribeirao preto": 84,
    "sao bernardo do campo": 89,
    "sao caetano do sul": 91,
    "sao caetano": 91,
    "santo andre": 85,
    "osasco": 83,
    "barueri": 90,  # Alphaville puxa muito
    "guarulhos": 82,

    "rio de janeiro": 88,
    "niteroi": 86,
    "niterói": 86,
    "petropolis": 80,
    "petrópolis": 80,
    "teresopolis": 79,
    "teresópolis": 79,
    "nova iguacu": 52,
    "nova iguaçu": 52,
    "duque de caxias": 50,
    "sao goncalo": 49,
    "são gonçalo": 49,
    "volta redonda": 78,
    "barra mansa": 54,

    # Espírito Santo
    "vitoria": 94,
    "vitória": 94,
    "vila velha": 91,
    "guarapari": 88,
    "domingos martins": 88,
    "venda nova do imigrante": 80,
    "serra": 64,
    "colatina": 62,
}


_RAW_NEIGHBORHOOD_SCORES_MG = {
    "belo horizonte": {
        # Centro-Sul e eixos fortes
        "Lourdes": 97,
        "Savassi": 97,
        "Funcionários": 96,
        "Santo Agostinho": 95,
        "Belvedere": 94,
        "Sion": 93,
        "Cruzeiro": 92,
        "Anchieta": 92,
        "Carmo": 91,
        "Luxemburgo": 90,
        "Serra": 90,
        "São Pedro": 89,
        "Santo Antônio": 88,

        # Muito bons
        "Cidade Nova": 88,
        "Gutierrez": 88,
        "Castelo": 87,
        "Buritis": 86,
        "Santa Tereza": 86,
        "Floresta": 84,
        "Prado": 84,
        "Santa Efigênia": 84,
        "Colégio Batista": 84,
        "Sagrada Família": 84,
        "Palmares": 82,
        "Ipiranga": 82,
        "União": 81,
        "Jaraguá": 81,
        "Nova Suíssa": 80,
        "Ouro Preto": 84,
        "Dona Clara": 85,

        # Bons / médios altos
        "Barro Preto": 81,
        "Grajaú": 81,
        "São Lucas": 78,
        "Jardim América": 78,
        "Caiçara": 82,
        "Padre Eustáquio": 82,
        "Itapoã": 76,
        "Santa Amélia": 76,
        "Planalto": 75,
        "Fernão Dias": 75,
        "Havaí": 74,

        # Centro e regiões heterogêneas
        "Centro": 76,

        # Estrutura razoável, mas abaixo do topo para moradia
        "Barreiro": 69,
        "Venda Nova": 67,
        "Betânia": 78,
        "Nova Granada": 77,
        "Calafate": 78,
        "Santa Inês": 79,
        "São Bento": 90,
        "Comiteco": 88,
        "Mangabeiras": 92,
        "São Luiz": 83,
        "Liberdade": 83,
        "Pampulha": 84,
        "Trevo": 73,
        "Candelária": 70,
        "Letícia": 69,
        "Santa Mônica": 74,
        "Rio Branco": 68,
        "Heliópolis": 72,
        "Minas Brasil": 75,
        "Alípio de Melo": 76,
        "Coqueiros": 74,
    },

    "contagem": {
        # Melhor posicionados para moradia
        "Cabral": 85,
        "Eldorado": 84,
        "Centro": 79,
        "Riacho das Pedras": 78,
        "Inconfidentes": 77,
        "Arvoredo": 76,
        "Água Branca": 75,
        "Amazonas": 74,
        "Glória": 74,
        "Novo Riacho": 74,
        "Jardim Riacho das Pedras": 79,
        "Santa Cruz Industrial": 70,
        "Ressaca": 73,
        "Xangri-lá": 71,
        "Europa": 71,
        "Bernardo Monteiro": 70,
        "Colonial": 70,
        "Fonte Grande": 70,
        "Industrial": 66,
        "Cidade Industrial": 64,
        "Industrial Santa Maria": 65,
        "Santa Maria": 69,
        "Bandeirantes": 70,
        "Petrolândia": 72,
        "Nacional": 68,
        "Confisco": 69,
        "Pedra Azul": 66,
        "Jardim Industrial": 67,
        "Parque Xangri-lá": 70,
        "Caiapós": 67,
        "Vila Pérola": 66,
        "Camilo Alves": 67,
        "Canadá": 68,
        "Santa Helena": 69,
        "Santa Luzia": 68,
        "São Gonçalo": 69,
        "São Mateus": 70,
        "São Bernardo": 69,
        "Ouro Branco": 70,
        "Linda Vista": 71,
        "Perobas": 67,
        "Quintas Coloniais": 66,
        "Funcionários": 72,
        "Parque Maracanã": 70,
        "Central Park": 71,
        "Alvorada": 72,
        "Betânia": 72,
        "Colonial": 70,
        "Arcádia": 68,
        "Bitácula": 66,
        "Chácaras Califórnia": 64,
        "Chácaras Contagem": 64,
        "Conjunto Fonte Grande": 66,
        "Parque Recreio": 67,
        "Sapucaias": 65,
        "Jardim Vera Cruz": 66,
        "Novo Progresso": 65,
    },

   "ipatinga": {
        # Topo
        "Cidade Nobre": 91,
        "Cariru": 90,
        "Castelo": 88,
        "Bairro das Águas": 88,
        "Horto": 87,

        # Muito bons / bons
        "Ideal": 82,
        "Bom Retiro": 81,
        "Iguaçu": 80,
        "Igarapé": 80,
        "Veneza": 79,
        "Bethânia": 79,
        "Canaã": 78,
        "Das Águas": 78,
        "Parque das Águas": 76,
        "Jardim Panorama": 75,
        "Centro": 77,

        # Médios
        "Esperança": 73,
        "Vila Celeste": 70,
        "Bom Jardim": 69,
        "Limoeiro": 68,
        "Nova Esperança": 68,
        "Jardim Vitória": 67,
        "Jardim Brasília": 67,
    },

    "nova lima": {
        "vila da serra": 97,
        "vale do sereno": 96,
        "belvedere": 92,  # quando vier cadastrado assim no anúncio
        "jardim canada": 77,
        "jardim canadá": 77,
        "centro": 76,
        "cristais": 74,
        "honorio bicalho": 68,
        "honório bicalho": 68,
        "bairro oswaldo barbosa pena": 72,
        "retiro": 70,
        "bela fama": 66,
        "vila operaria": 64,
        "vila operária": 64,
        "vila sao luiz": 66,
        "vila são luiz": 66,
    },

    "betim": {
        "centro": 77,
        "inga": 75,
        "ingá": 75,
        "jardim alterosas": 73,
        "brasileia": 74,
        "brasileia": 74,
        "castro pires": 70,
        "cidade verde": 73,
        "pti": 69,
        "petropolis": 70,
        "petrópolis": 70,
    },

    "uberlandia": {
        "fundinho": 92,
        "santa monica": 89,
        "santa mônica": 89,
        "morada da colina": 91,
        "tibery": 85,
        "centro": 81,
        "martins": 80,
        "lidice": 84,
        "lídice": 84,
        "jaragua": 79,
        "jaraguá": 79,
        "patrimonio": 78,
        "patrimônio": 78,
        "vigilato pereira": 84,
        "cazeca": 77,
        "roosevelt": 73,
        "luizote de freitas": 71,
        "segismundo pereira": 76,
        "granada": 78,
        "karaiba": 83,
        "karaíba": 83,
    },

    "juiz de fora": {
        "bom pastor": 91,
        "sao mateus": 89,
        "são mateus": 89,
        "alto dos passos": 87,
        "cascatinha": 89,
        "centro": 81,
        "granbery": 85,
        "jardim gloria": 84,
        "jardim glória": 84,
        "mariano procopio": 78,
        "mariano procópio": 78,
        "santa helena": 82,
        "sao pedro": 79,
        "são pedro": 79,
        "benfica": 70,
    },

    "pocos de caldas": {
        "centro": 83,
        "jardim dos estados": 89,
        "country club": 88,
        "jardim quisisana": 86,
        "vila cruz": 74,
    },

    "varginha": {
        "centro": 80,
        "vila pinto": 75,
        "jardim anderi": 77,
        "sion": 78,
    },

    "lavras": {
        "centro": 79,
        "zona norte": 70,
        "nova lavras": 73,
    },

    "vicosa": {
        "centro": 81,
        "ramos": 78,
        "clélia bernardes": 77,
        "clelia bernardes": 77,
        "santo antonio": 74,
        "santo antônio": 74,
        "silvestre": 72,
    },

    "divinopolis": {
        "centro": 79,
        "sidil": 83,
        "bom pastor": 82,
        "sao jose": 76,
        "são josé": 76,
        "porto velho": 73,
    },

    "montes claros": {
        "centro": 78,
        "ibituruna": 88,
        "melo": 76,
        "todos os santos": 84,
        "augusta mota": 82,
        "morada do sol": 80,
    },

    "uberaba": {
        "centro": 79,
        "fabrício": 82,
        "fabricio": 82,
        "sao benedito": 74,
        "são benedito": 74,
        "mercês": 80,
        "merces": 80,
        "olinda": 76,
    },

    "governador valadares": {
        "centro": 77,
        "esplanada": 80,
        "grã-duquesa": 84,
        "gra-duquesa": 84,
        "ilha dos araujos": 85,
        "ilha dos araújos": 85,
        "morada do vale": 75,
    },

    "sete lagoas": {
        "centro": 78,
        "boa vista": 76,
        "mangabeiras": 83,
        "canfado": 72,
    },

    "pouso alegre": {
        "centro": 80,
        "fatima": 76,
        "fátima": 76,
        "santa doroteia": 82,
        "jardim olimpico": 78,
        "jardim olímpico": 78,
    },

    "patos de minas": {
        "centro": 79,
        "caicaras": 76,
        "caiçaras": 76,
        "rosario": 77,
        "rosário": 77,
        "brasilia": 74,
        "brasília": 74,
    },

    "araxa": {
        "centro": 79,
        "urciano lemos": 74,
        "santa terezinha": 76,
        "sao geraldo": 74,
        "são geraldo": 74,
    },

    "itabira": {
        "centro": 77,
        "penha": 75,
        "gabiroba": 72,
        "campestre": 74,
    },

    "conselheiro lafaiete": {
        "centro": 77,
        "sao dimas": 74,
        "são dimas": 74,
        "carijos": 72,
        "progresso": 73,
    },

    "santa luzia": {
        "centro": 72,
        "sao benedito": 70,
        "são benedito": 70,
        "frimisa": 68,
    },

    "ribeirao das neves": {
        "centro": 64,
        "justinopolis": 60,
        "justinópolis": 60,
        "veneza": 61,
    },

    "ibirite": {
        "centro": 68,
        "durval de barros": 63,
        "petropolis": 64,
        "petrópolis": 64,
    },

    "sabará": {
        "centro": 72,
        "nações unidas": 68,
        "nacoes unidas": 68,
        "alvorada": 67,
    },
}

_RAW_NEIGHBORHOOD_SCORES_SP = {
    "sao paulo": {
        # 🔥 PREMIUM
        "Itaim Bibi": 98,
        "Vila Nova Conceicao": 98,
        "Jardins": 97,
        "Jardim Paulista": 97,
        "Jardim Europa": 97,
        "Jardim America": 97,
        "Moema": 96,
        "Vila Olimpia": 96,
        "Brooklin": 95,
        "Campo Belo": 95,
        "Pinheiros": 95,
        "Perdizes": 94,
        "Higienopolis": 94,
        "Vila Madalena": 93,
        "Aclimacao": 92,

        # 🟢 ALTO PADRÃO
        "Saude": 90,
        "Chacara Klabin": 91,
        "Paraiso": 93,
        "Bela Vista": 88,
        "Liberdade": 87,
        "Consolacao": 90,
        "Sumare": 92,
        "Alto de Pinheiros": 94,

        # 🟡 MÉDIO BOM
        "Ipiranga": 86,
        "Tatuape": 88,
        "Analia Franco": 90,
        "Mooca": 88,
        "Vila Mariana": 92,
        "Cambuci": 80,
        "Santa Cecilia": 87,
        "Barra Funda": 85,

        # 🟠 ZONA OESTE EXPANSÃO
        "Butanta": 84,
        "Rio Pequeno": 76,
        "Jaguaré": 80,
        "Vila Leopoldina": 90,
        "Lapa": 88,

        # 🔵 ZONA NORTE
        "Santana": 85,
        "Tucuruvi": 83,
        "Casa Verde": 82,
        "Mandaqui": 80,

        # 🔴 ZONA LESTE (heterogênea)
        "Penha": 78,
        "Vila Matilde": 79,
        "Itaquera": 72,
        "Artur Alvim": 71,
        "Guaianases": 65,

        # ⚠️ BAIXO SCORE
        "Cidade Tiradentes": 60,
        "Capao Redondo": 65,
        "Jardim Angela": 64,
    }
}

_RAW_NEIGHBORHOOD_SCORES_RJ = {
    "rio de janeiro": {
        # Premium / muito bons
        "leblon": 99,
        "ipanema": 98,
        "lagoa": 97,
        "jardim Botanico": 96,
        "gavea": 95,
        "humaita": 92,
        "botafogo": 91,
        "flamengo": 90,
        "laranjeiras": 90,
        "copacabana": 89,

        # Médios
        "praca seca": 41,
        "praça seca": 41,

        "barra da tijuca": 91,
        "recreio dos bandeirantes": 86,
        "freguesia jacarepagua": 49,
        "itanhanga": 77,
        "tijuca": 75,
        "vila isabel": 49,
        "meier": 45,
        "méier": 45,
        "cachambi": 44,
        "rio comprido": 31,
        "bancarios": 34,
        "bancários": 34,

        # intermediários
        "jacarepagua": 59,
        "taquara": 40,
        "vila valqueire": 60,
        "penha": 22,
        "olaria": 34,
        "piedade": 34,
        "encantado": 33,
        "riachuelo": 36,
        "catumbi": 33,
        "abolicao": 33,
        "abolição": 33,
        "engenho de dentro": 32,
        "engenho novo": 38,
        "vicente de carvalho": 31,
        "vila kosmos": 31,
        "bras de pina": 39,
        "brás de pina": 39,
        "penha circular": 37,
        "madureira": 36,
        "campo grande": 39,
        "guaratiba": 34,
        "cordovil": 32,
        "cocota": 30,
        "cocotá": 30,
        "marechal hermes": 38,
        "deodoro": 22,
        "realengo": 34,
        "bangu": 22,
        "pilares": 29,
        "agua santa": 31,
        "água santa": 31,
        "sampaio": 30,
        "fonseca": 33,  # Niterói não entra aqui, mas mantive por segurança de matching errado

        # baixos
        "praca seca": 22,
        "vaz lobo": 35,
        "guadalupe": 38,
        "pavuna": 32,
        "senador camara": 34,
        "senador câmara": 34,
        "santa cruz": 34,
        "paciencia": 33,
        "paciência": 33,
        "inhoaiba": 32,
        "inhoaíba": 32,
        "cavalcanti": 35,
        "coelho neto": 36,
        "anchieta": 37,
        "honorio gurgel": 36,
        "honório gurgel": 36,
        "cidade de deus": 30,
        "turiacu": 36,
        "turiaçu": 36,
        "tomas coelho": 37,
        "tomás coelho": 37,
        "santissimo": 34,
        "santíssimo": 34,
    },
    "niteroi": {
        "fonseca": 64,
        "santa rosa": 65,
        "centro": 70,
    },
}

_RAW_NEIGHBORHOOD_SCORES_ES = {
    "vitoria": {
        # topo
        "praia do canto": 96,
        "mata da praia": 95,
        "jardim camburi": 91,
        "barro vermelho": 93,
        "enseada do sua": 90,
        "ilha do boi": 98,
        "ilha do frade": 98,
        "bento ferreira": 88,
        "santa lucia": 88,
        "santa luiza": 87,
        "jucutuquara": 76,
        "fradinhos": 84,
        "horto": 82,
        "jesus de nazareth": 74,
        "consolacao": 74,
        "consolação": 74,
        "praia do sua": 86,
        "praia do suá": 86,

        # médios
        "centro": 72,
        "parque moscoso": 70,
        "fonte grande": 63,
        "ilha do principe": 66,
        "ilha do príncipe": 66,
        "vila rubim": 62,
        "do moscoso": 66,
        "romao": 63,
        "romão": 63,
        "forte sao joao": 66,
        "forte são joão": 66,
        "gurigica": 60,
        "itabirere": 58,
        "itarare": 60,
        "itararé": 60,
        "bonfim": 67,
        "santo antonio": 60,
        "santo antônio": 60,
        "grande vitoria": 61,
        "grande vitória": 61,
        "bela vista": 62,
        "caratoira": 58,
        "caratoíra": 58,
        "estrelinha": 56,
    },

    "vila velha": {
        # topo
        "praia da costa": 95,
        "itapoa": 90,
        "itapoa": 90,
        "praia de itaparica": 92,
        "itaparica": 91,
        "coqueiral de itaparica": 88,
        "praia das gaivotas": 88,
        "centro de vila velha": 77,
        "centro": 77,
        "gloria": 76,
        "glória": 76,
        "praia do ribeiro": 78,
        "jockey de itaparica": 78,
        "divino espirito santo": 79,
        "divino espírito santo": 79,

        # médios
        "soteco": 72,
        "boa vista": 73,
        "ilha dos aires": 76,
        "ilha dos ayres": 76,
        "cocal": 68,
        "ibes": 71,
        "nova itaparica": 75,
        "santa monica": 72,
        "santa mônica": 72,
        "ataide": 66,
        "ataíde": 66,
        "jardim asteca": 69,
        "vale encantado": 68,

        # baixos / médios-baixos
        "sao torquato": 60,
        "são torquato": 60,
        "cobilandia": 58,
        "cobilândia": 58,
        "argolas": 55,
        "ulisses guimaraes": 54,
        "ulisses guimarães": 54,
        "barramares": 63,
        "riviera da barra": 64,
    },

    "guarapari": {
        "praia do morro": 90,
        "centro": 88,
        "enseada azul": 92,
        "meaipe": 89,
        "nova guarapari": 87
    }
}

NEIGHBORHOOD_SCORES_MG = {
    normalize_text(city): _expand_city_neighborhood_scores(city_map)
    for city, city_map in _RAW_NEIGHBORHOOD_SCORES_MG.items()
}

NEIGHBORHOOD_SCORES_ES = {
    normalize_text(city): _expand_city_neighborhood_scores(city_map)
    for city, city_map in _RAW_NEIGHBORHOOD_SCORES_ES.items()
}

NEIGHBORHOOD_SCORES_SP = {
    normalize_text(city): _expand_city_neighborhood_scores(city_map)
    for city, city_map in _RAW_NEIGHBORHOOD_SCORES_SP.items()
}

NEIGHBORHOOD_SCORES_RJ = {
    normalize_text(city): _expand_city_neighborhood_scores(city_map)
    for city, city_map in _RAW_NEIGHBORHOOD_SCORES_RJ.items()
}


def neighborhood_structure_score(city: str | None, neighborhood: str | None, uf: str | None = None) -> float | None:
    city_norm = normalize_text(city or "")
    neighborhood_norm = normalize_text(neighborhood or "")

    if not city_norm or not neighborhood_norm:
        return None

    if uf == "MG":
        city_map = NEIGHBORHOOD_SCORES_MG.get(city_norm)
    elif uf == "SP":
        city_map = NEIGHBORHOOD_SCORES_SP.get(city_norm)
    elif uf == "RJ":
        city_map = NEIGHBORHOOD_SCORES_RJ.get(city_norm)
    else:
        city_map = None

    if city_map and neighborhood_norm in city_map:
        return float(city_map[neighborhood_norm])

    return None

def municipality_structure_score(city: str | None, uf: str | None = None) -> float:
    city_norm = clean_city_name(city)
    if not city_norm:
        return 35.0
    return float(CITY_STRUCTURE_SCORES.get(city_norm, 60.0))


def neighborhood_structure_score(city: str | None, neighborhood: str | None, uf: str | None = None) -> float | None:
    city_norm = clean_city_name(city)
    neighborhood_norm = clean_neighborhood_name(neighborhood)

    if not city_norm or not neighborhood_norm:
        return None

    uf_norm = normalize_text(uf or "")

    if uf_norm == "mg":
        city_map = NEIGHBORHOOD_SCORES_MG.get(city_norm)
    elif uf_norm == "sp":
        city_map = NEIGHBORHOOD_SCORES_SP.get(city_norm)
    elif uf_norm == "rj":
        city_map = NEIGHBORHOOD_SCORES_RJ.get(city_norm)
    elif uf_norm == "es":
        city_map = NEIGHBORHOOD_SCORES_ES.get(city_norm)
    else:
        city_map = None

    if city_map:
        return city_map.get(neighborhood_norm)

    return None