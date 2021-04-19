interface Foo {
    some: number;
    other: string;
}

export function test() {
    let x: Foo = { some: 1, other: "text" };
    alert(x.other);
}