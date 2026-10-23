"""service.yaml: fonte de configuracao do servico instalado da empresa."""

from pathlib import Path

from app.core import service_config

# Senha e nome do executavel mudam entre plataformas; o que importa aqui e a
# hierarquia de valores (default < yaml < env) e a tolerancia a erro.


def test_padroes_quando_nao_ha_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SERVICE_PASTA_BASE", raising=False)

    config = service_config.carregar(env={"SECRET": "x"})

    assert config.pasta_base is None
    assert config.porta == 8000
    assert config.equipe_padrao == "Documentos da empresa"
    assert config.intervalo_watch == service_config.INTERVALO_WATCH_PADRAO
    assert config.invalida == []


def test_yaml_completo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "service.yaml").write_text(
        "pasta_base: C:/Documentos da empresa\n"
        "porta: 9000\n"
        "equipe_padrao: Contabilidade\n"
        "intervalo_watch: 30\n",
        encoding="utf-8",
    )

    config = service_config.carregar(env={})

    assert config.pasta_base == Path("C:/Documentos da empresa")
    assert config.porta == 9000
    assert config.equipe_padrao == "Contabilidade"
    assert config.intervalo_watch == 30
    assert config.origem.startswith("service.yaml")


def test_env_sobrepoe_o_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "service.yaml").write_text(
        "porta: 9000\nequipe_padrao: Contabilidade\n", encoding="utf-8"
    )

    config = service_config.carregar(env={
        "SERVICE_PORTA": "9999",
        "SERVICE_EQUIPE_PADRAO": "Financeiro",
        "SERVICE_PASTA_BASE": "/dados/docs",
    })

    assert config.porta == 9999
    assert config.equipe_padrao == "Financeiro"
    assert config.pasta_base == Path("/dados/docs")


def test_yaml_quebrado_nao_derruba_o_boot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "service.yaml").write_text(
        "pasta_base: [\n  invalido\n", encoding="utf-8"
    )

    config = service_config.carregar(env={})

    assert config.pasta_base is None
    assert config.invalida and "ilegivel" in config.invalida[0]
    assert config.porta == 8000


def test_valores_invalidos_sao_ignorados_e_avisados(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "service.yaml").write_text(
        "porta: nao-e-porta\n"
        "intervalo_watch: -5\n"
        "equipe_padrao: ''\n"
        "pasta_base: 42\n",
        encoding="utf-8",
    )

    config = service_config.carregar(env={})

    assert set(config.invalida) == {"porta", "intervalo_watch", "equipe_padrao", "pasta_base"}
    assert config.porta == 8000
    assert config.equipe_padrao == "Documentos da empresa"
