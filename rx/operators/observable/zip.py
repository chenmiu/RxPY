from typing import Union, Iterable, Any
from rx.core import Observable, ObservableBase, AnonymousObservable
from rx.core.typing import Mapper
from rx.disposables import CompositeDisposable, SingleAssignmentDisposable


def zip(*args: Union[Iterable[Any], ObservableBase],  # pylint: disable=W0622
        result_mapper: Mapper = None) -> ObservableBase:
    """Merges the specified observable sequences into one observable
    sequence by using the mapper function whenever all of the
    observable sequences have produced an element at a corresponding
    index.

    The last element in the arguments must be a function to invoke for
    each series of elements at corresponding indexes in the sources.

    1 - res = zip(obs1, obs2, result_mapper=fn)
    2 - res = zip(xs, [1,2,3], result_mapper=fn)

    Keyword arguments:
    args -- Observable sources to zip.
    result_mapper -- Mapper function that produces an element
        whenever all of the observable sequences have produced an
        element at a corresponding index

    Returns an observable sequence containing the result of
    combining elements of the sources using the specified result
    mapper function.
    """

    if len(args) == 2 and isinstance(args[1], Iterable):
        return _zip_with_list(args[0], args[1], result_mapper=result_mapper)

    sources = list(args)
    result_mapper = result_mapper or list

    def subscribe(observer, scheduler=None):
        n = len(sources)
        queues = [[] for _ in range(n)]
        is_done = [False] * n

        def next(i):
            if all([len(q) for q in queues]):
                try:
                    queued_values = [x.pop(0) for x in queues]
                    res = result_mapper(*queued_values)
                except Exception as ex:
                    observer.throw(ex)
                    return

                observer.send(res)
            elif all([x for j, x in enumerate(is_done) if j != i]):
                observer.close()

        def done(i):
            is_done[i] = True
            if all(is_done):
                observer.close()

        subscriptions = [None]*n

        def func(i):
            source = sources[i]
            sad = SingleAssignmentDisposable()
            source = Observable.from_future(source)

            def send(x):
                queues[i].append(x)
                next(i)

            sad.disposable = source.subscribe_(send, observer.throw, lambda: done(i), scheduler)
            subscriptions[i] = sad
        for idx in range(n):
            func(idx)
        return CompositeDisposable(subscriptions)
    return AnonymousObservable(subscribe)


def _zip_with_list(source, second, result_mapper):
    first = source

    def subscribe(observer, scheduler=None):
        length = len(second)
        index = 0

        def send(left):
            nonlocal index

            if index < length:
                right = second[index]
                index += 1
                try:
                    result = result_mapper(left, right)
                except Exception as ex:
                    observer.throw(ex)
                    return
                observer.send(result)
            else:
                observer.close()

        return first.subscribe_(send, observer.throw, observer.close, scheduler)
    return AnonymousObservable(subscribe)
