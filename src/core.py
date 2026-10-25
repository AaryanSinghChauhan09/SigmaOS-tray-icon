"""System tray icon host for SigmaOS-tray-icon (inspired by XAppStatusIcon).

Principles: registry encapsulation, fail-fast on duplicate registration and
unknown apps, validated icon names and menu models, event emission as a pure
return value (a thin D-Bus apply layer consumes it), deterministic ordering.
"""
import argparse, json, os, re, sys, tempfile

ENGINE = {
    "name": "sigma-tray",
    "summary": "Tray icon host: register icons, build menus, emit events",
    "language": "python",
    "verbs": ["register", "icon", "menu", "emit"],
    "principles": ["Encapsulation", "Information Hiding", "Fail-Fast",
                   "KISS", "Separation of Concerns", "Deterministic Testing"],
}

cli_doc = """\
$ sigma-tray register rhythmbox --icon media-player
$ sigma-tray icon rhythmbox --set media-player-paused
$ sigma-tray menu rhythmbox --item "play:Play" --item "pause:Pause"
$ sigma-tray emit rhythmbox --event menu-action --payload play
"""

DEFAULT_STORE = os.path.expanduser("~/.config/sigma-tray/registry.json")
_APPID_RE = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
_ICON_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
EVENTS = ("activate", "secondary-activate", "menu-action", "scroll-up", "scroll-down")


class TrayError(ValueError):
    pass


def register(registry, app_id, icon="application-x-executable"):
    """Register a tray icon. Fail-fast on bad ids and duplicates."""
    if not _APPID_RE.match(app_id):
        raise TrayError(f"bad app id: {app_id!r} (want: ^[a-z][a-z0-9-]+$)")
    if app_id in registry:
        raise TrayError(f"already registered: {app_id}")
    if not _ICON_RE.match(icon):
        raise TrayError(f"bad icon name: {icon!r}")
    registry[app_id] = {"icon": icon, "tooltip": "", "visible": True, "menu": []}
    return registry[app_id]


def set_icon(registry, app_id, icon):
    if app_id not in registry:
        raise TrayError(f"unknown app: {app_id}")
    if not _ICON_RE.match(icon):
        raise TrayError(f"bad icon name: {icon!r}")
    registry[app_id]["icon"] = icon
    return icon


def build_menu(items):
    """Validate and normalise an ordered menu model. Pure."""
    out, seen = [], set()
    for it in items:
        iid, label = it.get("id"), it.get("label")
        if not iid or not str(label).strip():
            raise TrayError(f"menu items need id+label: {it!r}")
        if iid in seen:
            raise TrayError(f"duplicate menu item id: {iid}")
        seen.add(iid)
        out.append({"id": iid, "label": str(label),
                    "action": str(it.get("action", iid))})
    return out


def set_menu(registry, app_id, items):
    if app_id not in registry:
        raise TrayError(f"unknown app: {app_id}")
    registry[app_id]["menu"] = build_menu(items)
    return registry[app_id]["menu"]


def emit(registry, app_id, event, payload=None):
    """Pure event construction; returns the delivery record (no I/O)."""
    if app_id not in registry:
        raise TrayError(f"unknown app: {app_id}")
    if event not in EVENTS:
        raise TrayError(f"unknown event: {event} (have: {', '.join(EVENTS)})")
    menu_ids = {m["id"] for m in registry[app_id]["menu"]}
    if event == "menu-action" and payload not in menu_ids:
        raise TrayError(f"menu action not in menu: {payload!r}")
    return {"app": app_id, "event": event, "payload": payload,
            "icon": registry[app_id]["icon"]}


def dispatch(records, sink=None):
    """Execute layer: hand records to a D-Bus sink.

    self_test uses a list.append sink, never a real D-Bus connection.
    """
    if sink is None:
        def sink(rec):
            print(f"[tray] {rec['app']}: {rec['event']} {rec['payload']}")
    n = 0
    for rec in records:
        sink(rec)
        n += 1
    return n


def load_registry(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    reg = {}
    for app_id, info in data.items():  # fail-fast on corrupt store
        register(reg, app_id, icon=info.get("icon", "application-x-executable"))
        reg[app_id]["tooltip"] = info.get("tooltip", "")
        reg[app_id]["visible"] = bool(info.get("visible", True))
        reg[app_id]["menu"] = build_menu(info.get("menu", []))
    return reg


def save_registry(path, registry):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".sigma-tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(registry, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=ENGINE["name"], description=ENGINE["summary"])
    p.add_argument("--store", default=DEFAULT_STORE, help="registry store (JSON)")
    sub = p.add_subparsers(dest="cmd", required=True)
    rg = sub.add_parser("register", help="register a tray icon")
    rg.add_argument("app_id")
    rg.add_argument("--icon", default="application-x-executable")
    ic = sub.add_parser("icon", help="set the icon of a registered app")
    ic.add_argument("app_id")
    ic.add_argument("--set", required=True, dest="icon")
    mn = sub.add_parser("menu", help="set the menu of a registered app")
    mn.add_argument("app_id")
    mn.add_argument("--item", action="append", required=True,
                    help="menu item id:Label (repeatable)")
    em = sub.add_parser("emit", help="emit an event for a registered app")
    em.add_argument("app_id")
    em.add_argument("--event", required=True, choices=EVENTS)
    em.add_argument("--payload", default=None)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        reg = load_registry(args.store)
        if args.cmd == "register":
            info = register(reg, args.app_id, icon=args.icon)
            save_registry(args.store, reg)
            print(f"registered {args.app_id} icon={info['icon']}")
        elif args.cmd == "icon":
            icon = set_icon(reg, args.app_id, args.icon)
            save_registry(args.store, reg)
            print(f"{args.app_id} icon={icon}")
        elif args.cmd == "menu":
            items = []
            for raw in args.item:
                iid, sep, label = raw.partition(":")
                if not sep:
                    raise TrayError(f"bad --item {raw!r} (want id:Label)")
                items.append({"id": iid, "label": label})
            menu = set_menu(reg, args.app_id, items)
            save_registry(args.store, reg)
            for m in menu:
                print(f"{m['id']}\t{m['label']}\taction={m['action']}")
        elif args.cmd == "emit":
            rec = emit(reg, args.app_id, args.event, args.payload)
            dispatch([rec])
        return 0
    except (TrayError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def self_test() -> None:
    reg = {}
    info = register(reg, "rhythmbox", icon="media-player")
    assert info["icon"] == "media-player" and info["visible"] is True
    # fail-fast: duplicate, bad app id, bad icon
    for bad in (lambda: register(reg, "rhythmbox"),
                lambda: register(reg, "RhythmBox"),
                lambda: register(reg, "ok-id", icon="../evil")):
        try:
            bad()
        except TrayError:
            pass
        else:
            raise AssertionError("expected TrayError")
    # icon switching
    assert set_icon(reg, "rhythmbox", "media-player-paused") == "media-player-paused"
    try:
        set_icon(reg, "ghost", "icon")
    except TrayError:
        pass
    else:
        raise AssertionError("unknown app not caught")
    # menu model: validated, ordered, duplicates rejected
    menu = set_menu(reg, "rhythmbox", [{"id": "play", "label": "Play"},
                                       {"id": "pause", "label": "Pause"}])
    assert [m["id"] for m in menu] == ["play", "pause"]
    assert menu[0]["action"] == "play"                       # default action
    for bad_items in ([{"id": "play", "label": "Play"},
                       {"id": "play", "label": "Again"}],
                      [{"id": "", "label": "x"}],
                      [{"id": "x", "label": " "}]):
        try:
            build_menu(bad_items)
        except TrayError:
            pass
        else:
            raise AssertionError(f"should reject menu {bad_items}")
    # emission is pure; dispatch uses an injected sink
    rec = emit(reg, "rhythmbox", "menu-action", payload="play")
    assert rec == {"app": "rhythmbox", "event": "menu-action", "payload": "play",
                   "icon": "media-player-paused"}
    for bad_rec in (lambda: emit(reg, "ghost", "activate"),
                    lambda: emit(reg, "rhythmbox", "explode"),
                    lambda: emit(reg, "rhythmbox", "menu-action", payload="stop")):
        try:
            bad_rec()
        except TrayError:
            pass
        else:
            raise AssertionError("expected TrayError for bad emit")
    seen = []
    assert dispatch([rec, rec], sink=seen.append) == 2
    assert seen == [rec, rec]
    # persistence round-trip (tempdir only)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "registry.json")
        save_registry(path, reg)
        again = load_registry(path)
        assert emit(again, "rhythmbox", "menu-action", "pause")["icon"] == "media-player-paused"
        assert load_registry(os.path.join(d, "none.json")) == {}


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
