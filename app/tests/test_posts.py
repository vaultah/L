import pytest
from app.el import posts
from app.el.accounts.records import Record
from app.el.images import Image

def test_create():
    acct = Record.new()
    objects = next(Image.new()),
    post = posts.Post.new(acct, content='<string>', images=objects)
    assert post.good()


@pytest.mark.parametrize('base_type', 
    [Image, posts.Post],
    ids=['base image', 'base posts']
)
def test_create_base(base_type):
    base = base_type.new()
    # Won't fail if base_type is Image
    try:
        base = next(base)
    except TypeError:
        pass

    reply = posts.Post.new(base.owner, content='<string>', ext=base)
    assert reply.good()
    assert reply.is_reply()
    shared = posts.Post.new(base.owner, content=None, ext=base)
    assert shared.good()
    assert not shared.is_reply()


def test_delete():
    obj = posts.Post.new()
    owner = obj.owner
    posts.Post.delete(owner, [obj])
    assert not posts.Post(obj.id).good()


def test_class():
    instance = posts.Post.new()
    new = posts.Post(instance.id)
    assert new.good()
    assert new == instance


def test_load_plain():
    objects = [posts.Post.new()]
    owner = objects[0].owner
    loaded = list(posts.page(owner))
    assert len(loaded)
    assert all(isinstance(x, posts.Post) for x in loaded)
    assert all(x.owner == owner for x in loaded)
    assert all(x.good() for x in loaded)
    assert set(objects) == set(loaded)

    # Testing iter_info here
    res = posts.iter_info(objects)
    assert res


def test_load_parents():
    bases = [next(Image.new())]
    owner = bases[-1].owner
    for _ in range(5):
        # Create a reply and make it a new base
        reply = posts.Post.new(owner, content='<string>', ext=bases[-1])
        bases.append(reply)
    
    for x in range(1, 5):
        parents = list(posts.parents(bases[x - 1]))
        assert len(parents) == x
        assert isinstance(parents[0], Image)
        assert all(isinstance(x, posts.Post) for x in parents[1:])
        # Everything but image
        assert all(x.is_reply() for x in parents[1:])


def test_load_derived():
    bases, derived = [next(Image.new())], []
    owner = bases[-1].owner
    for _ in range(5):
        # 'Share' base
        shared = posts.Post.new(owner, content=None, ext=bases[-1])
        # Create a reply and make it a new base
        reply = posts.Post.new(owner, content='<string>', ext=bases[-1])
        bases.append(reply)
        # There're 2 item on each level
        derived.append([shared, reply])

    # Without shared
    levels = list(posts.derived(bases[0]))
    assert len(levels) - 1 == len(derived)
    assert all(len(level) == 1 for level in levels[1:])
    # With shared
    levels = list(posts.derived(bases[0], reflections=True))
    assert all(len(level) == 2 for level in levels[1:])
    assert levels[1:] == derived
    # Testing level_info here
    res = list(posts.level_info(levels))
    assert res


def test_delete_derived():
    bases = [posts.Post.new()]
    owner = bases[-1].owner
    for _ in range(5):
        reply = posts.Post.new(owner, content='<string>', ext=bases[-1])
        bases.append(reply)

    posts.delete_derived(bases[0])
    assert all(not posts.Post(x.id).good() for x in bases)