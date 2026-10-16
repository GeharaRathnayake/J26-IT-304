# Blind rating sheet (D2 criterion 5)

How well does this reply explain the topic to a beginner, using the named strategy? 1 = poor, 5 = excellent.

**Do not open `blind_key_2026-10-15.json` until every item is rated.**

The 24 items below appear in random order.

## R01: exception_handling / simplified

In Java, exceptions are events that occur during the execution of your program. They can be thought of as errors that need to be handled so your program doesn't crash. You can use special blocks of code called try-catch blocks to catch exceptions and stop them from stopping your program.

**Check:** Which step of that explanation would you like me to go over again?

Rating (1-5): 

## R02: loops / analogy

Loops in Java are like folding laundry. You have a pile of clothes, and you want to put them away in your drawers. You can do this by taking the top item off the pile and putting it away, then taking the next item off the pile and putting it away, and so on.

```java
for (int i = 0; i < 5; i++) {
    System.out.println("Folding item " + i);
}
```

**Check:** How would you map this comparison back to the Java code?

Rating (1-5): 

## R03: exception_handling / analogy

Exception handling is like a safety net under a trapeze artist: if something goes wrong, the net catches the fall and the show goes on. The `try` block is the performance, the exception is the fall, and the `catch` block is the net. A `finally` block is like the cleanup crew that works after every show, whether or not anyone fell.

**Check:** What happens in this analogy if no net is set up?

Rating (1-5): 

## R04: inheritance / analogy

Inheritance is like a family relationship. A parent class is like a parent, and a child class is like a kid. The child class inherits all the qualities and characteristics of the parent class, like name, age, and family traits, and can also add new traits or change existing ones.

```java
public class Animal {
    public void eat() {}
}

public class Dog extends Animal {
    public void bark() {}
}
```

**Check:** Does a child class always inherit all the properties of its parent class?

Rating (1-5): 

## R05: inheritance / simplified

Inheritance means one class borrows what another class already has. The class that borrows is the child, and the class it borrows from is the parent. You write `extends` to connect them, like `class Dog extends Animal`.

**Check:** In `class Dog extends Animal`, which class is the child?

Rating (1-5): 

## R06: inheritance / example

Let's look at an example:

```java
class Animal {
    String name;
    Animal(String name) { this.name = name; }
}

class Dog extends Animal {
    Dog(String name) {
        super(name);
    }
}
```

The `super(name)` call runs the parent constructor first, so the inherited `name` field is set before `Dog` finishes building.

**Check:** What would happen if we removed the `super(name)` line?

Rating (1-5): 

## R07: inheritance / example



**Check:** What do you think would happen if you changed one line of this example?

Rating (1-5): 

## R08: inheritance / theory

Inheritance is a fundamental concept in object-oriented programming (OOP) where a new class inherits properties and behavior from an existing class. The key rules of inheritance are:

* A child class (subclass) inherits from a parent class (superclass).
* The child class can add new properties or override existing ones.
* The child class can also inherit behavior from the parent class.

**Check:** In your own words, what is the main idea here?

Rating (1-5): 

## R09: exception_handling / theory

Exception handling is a way to manage runtime errors in Java. It involves wrapping code in try-catch blocks to catch and handle exceptions. The key rule is to handle exceptions as close to the source as possible, and to provide meaningful error messages. Java provides built-in exception types, such as `RuntimeException` and `IOException`, which can be caught and handled using specific catch blocks.

```java
try {
    // code that might throw an exception
} catch (ExceptionType e) {
    // handle the exception
}
```

**Check:** In your own words, what is the main idea here?

Rating (1-5): 

## R10: loops / analogy

A loop is like running laps around a track: you keep going round until you have done the number of laps you planned. The lap you are on is the counter, the planned number of laps is the condition, and finishing one lap is one pass through the body. In Java, `for (int lap = 1; lap <= 3; lap++)` runs exactly three laps.

**Check:** In this analogy, what does `lap++` correspond to?

Rating (1-5): 

## R11: loops / theory

In Java, a loop is a control structure that allows you to execute a block of code repeatedly for a specified number of times. The key rules are:
* A loop has three main parts - initialization, condition, and increment/decrement.
* The loop continues as long as the condition is true.
* The loop can be a while loop, for loop, or do-while loop.

```java
while (true) {
    System.out.println("Hello, World!");
}
```

**Check:** In your own words, what is the main idea here?

Rating (1-5): 

## R12: loops / simplified

Loops in Java are used to repeat a set of instructions. Think of them like a merry-go-round: you get back on after each ride. In Java, we use the `for` loop to create this effect. Here's a simple example:
```java
public class SimpleLoop {
    public static void main(String[] args) {
        for (int i = 0; i < 5; i++) {
            System.out.println(i);
        }
    }
}
```
This will print the numbers 0 through 4.

**Check:** Which step of that explanation would you like me to go over again?

Rating (1-5): 

## R13: loops / example

```java
public class Example {
    public static void main(String[] args) {
        for (int i = 0; i < 5; i++) {
            System.out.println(i);
        }
    }
}
```

This example demonstrates a simple `for` loop that prints the numbers 0 to 4 to the console. It shows how to use a counter variable in a loop.

**Check:** What do you think would happen if you changed one line of this example?

Rating (1-5): 

## R14: inheritance / analogy

Inheritance is like a family: a child inherits traits from a parent, such as eye colour, but can also have traits of their own. In Java the parent is the superclass and the child is the subclass, and `extends` is the family link. A `Dog` that extends `Animal` automatically has what every `Animal` has, and can add barking on top.

**Check:** In this analogy, what does a trait the child has but the parent lacks correspond to in code?

Rating (1-5): 

## R15: loops / example

Here is a small example:

```java
public class Demo {
    public static void main(String[] args) {
        for (int i = 1; i <= 3; i++) {
            System.out.println("Round " + i);
        }
    }
}
```

The loop starts with `i` at 1, prints a line, adds 1 to `i`, and stops when `i` becomes 4, so it prints three lines.

**Check:** What would change if the condition were `i <= 5`?

Rating (1-5): 

## R16: exception_handling / example

Here is a small example:

```java
public class Demo {
    public static void main(String[] args) {
        try {
            int result = 10 / 0;
            System.out.println(result);
        } catch (ArithmeticException e) {
            System.out.println("Cannot divide by zero");
        }
    }
}
```

Dividing an `int` by zero throws an `ArithmeticException`, so the rest of the `try` block is skipped and the `catch` block prints its message.

**Check:** Would the line `System.out.println(result);` run, and why or why not?

Rating (1-5): 

## R17: loops / simplified

A loop is a way to say "do this again" without writing the same lines many times. You tell Java where to start, when to stop, and how to move forward each time. For example, `for (int i = 0; i < 3; i++)` starts at 0, stops before 3, and adds 1 each time.

**Check:** In that loop, what is the starting value of `i`?

Rating (1-5): 

## R18: inheritance / theory

Inheritance lets one class, the subclass, reuse the fields and methods of another class, the superclass, using the keyword `extends`. A subclass can use everything in its superclass that is not private, and it can add its own members or override inherited methods. Java allows a class to extend only one superclass. A subclass constructor must also run the parent constructor, and `super(...)` does that.

**Check:** In `class Dog extends Animal`, which class is the superclass?

Rating (1-5): 

## R19: exception_handling / example

```java
public class ExceptionHandlingExample {
    public static void main(String[] args) {
        int a = 10 / 0;
        try {
            System.out.println(a);
        } catch (ArithmeticException e) {
            System.out.println("Cannot divide by zero.");
        }
    }
}
```

This example shows how to handle a `ArithmeticException` that occurs when attempting to divide by zero. It demonstrates the use of a `try-catch` block to catch and handle the exception.

**Check:** What do you think would happen if you changed one line of this example?

Rating (1-5): 

## R20: exception_handling / analogy

Imagine you're baking a cake and you're not sure if the oven temperature is set correctly. You can't just guess and hope it turns out right. Instead, you use a thermometer to check the temperature and adjust the oven settings if needed. Similarly, in Java, when you're working with code that might throw errors, you use "try" blocks to anticipate potential problems and "catch" blocks to handle them gracefully. This helps prevent your program from crashing. `

**Check:** `

Rating (1-5): 

## R21: exception_handling / theory

An exception is an event that disrupts normal execution, such as dividing an integer by zero or reading a missing file. You wrap risky code in a `try` block and handle the problem in a `catch` block for the exception type you expect. An optional `finally` block runs whether or not an exception happened, which makes it useful for cleanup. If nothing catches an exception, the program stops with an error message.

**Check:** When does the `catch` block run?

Rating (1-5): 

## R22: exception_handling / simplified

An exception is Java's way of saying that something went wrong while the program was running. With `try`, you say "attempt this". With `catch`, you say "if that went wrong, do this instead".

**Check:** Which keyword holds the code that might fail?

Rating (1-5): 

## R23: loops / theory

A loop repeats a block of code. A `for` loop is used when you know how many times to repeat, and it has three parts: an initialiser, a condition checked before each pass, and an update run after each pass. A `while` loop repeats as long as its condition stays true, so something inside it must eventually make the condition false. Otherwise it never stops.

**Check:** How many times does the body of `for (int i = 0; i < 3; i++)` run?

Rating (1-5): 

## R24: inheritance / simplified

Inheritance is a way to create a new class that is based on an existing class. Think of it like a car and a truck - both are vehicles, but a truck is a type of car. In Java, you can create a new class that inherits the properties of an existing class by using the `extends` keyword.

**Check:** Which step of that explanation would you like me to go over again?

Rating (1-5): 
