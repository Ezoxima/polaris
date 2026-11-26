"""Tests de `generer_commandes` : la source unique `commandes/` et les fichiers générés restent synchronisés."""

from __future__ import annotations

from pathlib import Path

import pytest

import generer_commandes as gc

RACINE_DEPOT = Path(__file__).resolve().parent.parent


def source(nom="demo", type_="commande", description="Une démo", extra="", corps="Texte {{arguments}}.\n"):
    return f"---\ntype: {type_}\ndescription: {description}\n{extra}---\n{corps}"


def depot(tmp_path, **sources):
    (tmp_path / "commandes").mkdir()
    for nom, texte in sources.items():
        (tmp_path / "commandes" / f"{nom}.md").write_text(texte, encoding="utf-8")
    return tmp_path


# ---------- le dépôt réel ----------
def test_les_fichiers_generes_du_depot_sont_a_jour():
    attendus = gc.attendus(gc.charger_sources(RACINE_DEPOT / "commandes"))
    assert gc.verifier(RACINE_DEPOT, attendus) == []


def test_le_depot_contient_les_huit_commandes_et_la_skill():
    noms = {c.nom: c.type for c in gc.charger_sources(RACINE_DEPOT / "commandes")}
    assert noms == {
        "point": "commande",
        "quoi-faire": "commande",
        "note": "commande",
        "lancer": "commande",
        "go": "commande",
        "nouveau-projet": "commande",
        "conseil": "commande",
        "configurer": "commande",
        "creuser": "skill",
    }


def test_chaque_skill_copilot_respecte_les_regles_documentees():
    for cmd in gc.charger_sources(RACINE_DEPOT / "commandes"):
        chemin, contenu = gc.rendre(cmd, "copilot")
        assert chemin == f".github/skills/{cmd.nom}/SKILL.md"
        assert contenu.startswith(f'---\nname: "{cmd.nom}"\n')
        assert len(cmd.nom) <= 64 and len(cmd.description) <= 1024
        assert "{{arguments}}" not in contenu and "<!--claude" not in contenu and "<!--copilot" not in contenu


# ---------- analyse des sources ----------
def test_lire_source_nominale(tmp_path):
    f = tmp_path / "demo.md"
    f.write_text(source(extra="argument-hint: <x>\nmodele: fort\n"), encoding="utf-8")
    c = gc.lire_source(f)
    assert (c.nom, c.type, c.description, c.argument_hint, c.modele) == ("demo", "commande", "Une démo", "<x>", "fort")


def test_description_avec_deux_points_est_conservee(tmp_path):
    f = tmp_path / "demo.md"
    f.write_text(source(description="Avant : après"), encoding="utf-8")
    assert gc.lire_source(f).description == "Avant : après"


@pytest.mark.parametrize(
    "texte,fragment",
    [
        ("pas d'en-tête\n", "en-tête absent"),
        (source(type_="autre"), "`type`"),
        ("---\ntype: commande\n---\ncorps\n", "description"),
        (source(extra="inconnu: x\n"), "inconnu"),
        (source(extra="modele: gigantesque\n"), "modele"),
        (source(description="x" * 1025), "trop longue"),
        ("---\ntype: commande\nligne sans deux points\n---\ncorps", "illisible"),
        (source(corps="<!--claude-->jamais fermé\n"), "non appariées"),
    ],
)
def test_sources_invalides(tmp_path, texte, fragment):
    f = tmp_path / "demo.md"
    f.write_text(texte, encoding="utf-8")
    with pytest.raises(gc.ErreurSource, match=fragment):
        gc.lire_source(f)


def test_nom_de_fichier_invalide(tmp_path):
    f = tmp_path / "Mauvais Nom.md"
    f.write_text(source(), encoding="utf-8")
    with pytest.raises(gc.ErreurSource, match="nom invalide"):
        gc.lire_source(f)


def test_dossier_vide_ou_absent(tmp_path):
    with pytest.raises(gc.ErreurSource, match="aucune source"):
        gc.charger_sources(tmp_path / "commandes")


# ---------- rendu ----------
def test_arguments_et_blocs_par_cible(tmp_path):
    corps = (
        "A {{arguments}}\n<!--claude-->pour claude\n<!--/claude-->\n<!--copilot-->pour copilot\n<!--/copilot-->fin\n"
    )
    c = gc.Commande("demo", "commande", "d", None, None, corps)
    claude = gc.adapter_corps(corps, "claude")
    copilot = gc.adapter_corps(corps, "copilot")
    assert "`$ARGUMENTS`" in claude and "pour claude" in claude and "pour copilot" not in claude
    assert "après le nom de la commande" in copilot and "pour copilot" in copilot and "pour claude" not in copilot
    assert c.nom == "demo"


def test_rendu_commande_claude_et_skill_copilot():
    c = gc.Commande("demo", "commande", "Une démo", "<x>", "leger", "Corps\n")
    chemin, contenu = gc.rendre(c, "claude")
    assert chemin == ".claude/commands/demo.md"
    assert 'description: "Une démo"' in contenu and 'argument-hint: "<x>"' in contenu and 'model: "haiku"' in contenu
    assert gc.MARQUEUR in contenu and contenu.endswith("Corps\n")
    chemin, contenu = gc.rendre(c, "copilot")
    assert chemin == ".github/skills/demo/SKILL.md"
    assert 'name: "demo"' in contenu and "model" not in contenu


def test_skill_claude_dans_le_dossier_des_skills():
    c = gc.Commande("sujet", "skill", "d", None, None, "x\n")
    assert gc.rendre(c, "claude")[0] == ".claude/skills/sujet/SKILL.md"


def test_les_valeurs_d_entete_sont_du_yaml_valide_meme_avec_des_guillemets():
    c = gc.Commande("demo", "commande", 'Dit "oui" : vraiment', None, None, "x\n")
    assert 'description: "Dit \\"oui\\" : vraiment"' in gc.rendre(c, "claude")[1]


# ---------- écriture et vérification ----------
def test_ecrire_puis_verifier_puis_desynchroniser(tmp_path, capsys):
    racine = depot(tmp_path, demo=source(), creuser=source(type_="skill"))
    assert gc.main([], racine=racine) == 0
    assert (racine / ".claude/commands/demo.md").is_file() and (racine / ".github/skills/creuser/SKILL.md").is_file()
    assert gc.main(["--verifier"], racine=racine) == 0
    f = racine / ".claude/commands/demo.md"
    f.write_text(f.read_text(encoding="utf-8") + "\nmodifié à la main", encoding="utf-8")  # marque conservée
    assert gc.main(["--verifier"], racine=racine) == 1
    assert "désynchronisé : .claude/commands/demo.md" in capsys.readouterr().err
    assert gc.main([], racine=racine) == 0 and gc.main(["--verifier"], racine=racine) == 0


def test_verifier_signale_un_fichier_manquant(tmp_path, capsys):
    racine = depot(tmp_path, demo=source())
    assert gc.main(["--verifier"], racine=racine) == 1
    assert "manquant" in capsys.readouterr().err


def test_verifier_n_ecrit_rien(tmp_path):
    racine = depot(tmp_path, demo=source())
    gc.main(["--verifier"], racine=racine)
    assert not (racine / ".claude").exists()


def test_fins_de_ligne_windows_ne_desynchronisent_pas(tmp_path):
    racine = depot(tmp_path, demo=source())
    gc.main([], racine=racine)
    f = racine / ".claude/commands/demo.md"
    f.write_bytes(f.read_bytes().replace(b"\n", b"\r\n"))
    assert gc.main(["--verifier"], racine=racine) == 0


def test_orphelin_signale_jamais_supprime(tmp_path, capsys):
    racine = depot(tmp_path, demo=source(), autre=source())
    gc.main([], racine=racine)
    (racine / "commandes" / "autre.md").unlink()
    assert gc.main(["--verifier"], racine=racine) == 1
    assert "orphelin" in capsys.readouterr().err
    gc.main([], racine=racine)
    assert (racine / ".claude/commands/autre.md").is_file()  # signalé, jamais supprimé
    # un fichier écrit à la main (sans marqueur) n'est pas un orphelin
    (racine / ".claude/commands/perso.md").write_text("à moi", encoding="utf-8")
    assert "perso" not in "".join(gc.orphelins(racine, gc.attendus(gc.charger_sources(racine / "commandes"))))


def test_erreur_de_source_donne_le_code_2(tmp_path, capsys):
    racine = depot(tmp_path, demo="pas d'en-tête")
    assert gc.main([], racine=racine) == 2
    assert "ERREUR" in capsys.readouterr().err


# ---------- ne jamais écraser un fichier qui n'est pas à l'outil ----------
def test_un_fichier_homonyme_ecrit_a_la_main_est_preserve(tmp_path, capsys):
    racine = depot(tmp_path, demo=source(), autre=source())
    perso = racine / ".claude/commands/demo.md"
    perso.parent.mkdir(parents=True)
    perso.write_text("ma commande à moi", encoding="utf-8")
    assert gc.main([], racine=racine) == 3
    err = capsys.readouterr().err
    assert "REFUS" in err and ".claude/commands/demo.md" in err
    assert perso.read_text(encoding="utf-8") == "ma commande à moi"
    assert not (racine / ".claude/commands/autre.md").exists()  # rien n'est écrit, même pour les autres
    assert not (racine / ".github").exists()


def test_forcer_ecrase_le_fichier_homonyme(tmp_path):
    racine = depot(tmp_path, demo=source())
    perso = racine / ".claude/commands/demo.md"
    perso.parent.mkdir(parents=True)
    perso.write_text("ma commande à moi", encoding="utf-8")
    assert gc.main(["--forcer"], racine=racine) == 0
    assert gc.MARQUEUR in perso.read_text(encoding="utf-8")
    assert gc.main(["--verifier"], racine=racine) == 0


def test_fichier_genere_modifie_a_la_main_reste_reecrit(tmp_path):
    racine = depot(tmp_path, demo=source())
    gc.main([], racine=racine)
    f = racine / ".claude/commands/demo.md"
    f.write_text(f.read_text(encoding="utf-8") + "ajout manuel\n", encoding="utf-8")
    assert gc.main([], racine=racine) == 0
    assert "ajout manuel" not in f.read_text(encoding="utf-8")


def test_verifier_signale_a_part_le_fichier_non_genere(tmp_path, capsys):
    racine = depot(tmp_path, demo=source())
    perso = racine / ".claude/commands/demo.md"
    perso.parent.mkdir(parents=True)
    perso.write_text("à moi", encoding="utf-8")
    assert gc.main(["--verifier"], racine=racine) == 1
    err = capsys.readouterr().err
    assert "non généré par l'outil" in err and "désynchronisé : .claude/commands/demo.md" not in err
    assert perso.read_text(encoding="utf-8") == "à moi"
