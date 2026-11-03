from yak_tokenizer import LATEST, SIZES, VERSIONS, hub_folder


def test_versioned_names_resolve_to_themselves():
    for name in SIZES:
        assert hub_folder(name) == name


def test_bare_size_picks_newest_version_with_it():
    assert LATEST == "v2.0"
    assert hub_folder("128k") == "v2.0/128k"
    assert hub_folder("64k") == "v2.0/64k"
    assert hub_folder("32k") == "v1.0/32k"
    assert hub_folder("128k-phrase") == "v1.0/128k-phrase"


def test_unknown_names_are_not_hub_folders():
    assert hub_folder("ampixa/other-repo") is None
    assert hub_folder("v3.0/128k") is None
    assert sum(len(s) for s in VERSIONS.values()) == len(SIZES) == 7
