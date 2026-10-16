# Blind rating sheet (D2 criterion 5)

How well does this reply explain the topic to a beginner, using the named strategy? 1 = poor, 5 = excellent.

**Do not open `blind_key_2026-10-17.json` until every item is rated.**

The 24 items below appear in random order.

## R01: loops / simplified

A loop is a way to say "do this again" without writing the same lines many times. You tell Java where to start, when to stop, and how to move forward each time. For example, `for (int i = 0; i < 3; i++)` starts at 0, stops before 3, and adds 1 each time.

**Check:** In that loop, what is the starting value of `i`?

Rating (1-5): 

## R02: inheritance / theory

Inheritance lets one class, the subclass, reuse the fields and methods of another class, the superclass, using the keyword `extends`. A subclass can use everything in its superclass that is not private, and it can add its own members or override inherited methods. Java allows a class to extend only one superclass. A subclass constructor must also run the parent constructor, and `super(...)` does that.

**Check:** In `class Dog extends Animal`, which class is the superclass?

Rating (1-5): 

## R03: inheritance / analogy

Inheritance is like building a house. Imagine you want to build a similar house, but with a few extra rooms. You can't just replicate the entire house, as that would be inefficient. Instead, you can create a new house that's a variation of the original one. You take the original blueprint (the parent class) and modify it to create the new one (the child class). The child class has all the same features as the parent class, plus the new features you want. This way, you can reuse the original blueprint and focus on adding new features, making it easier to build new houses (classes) quickly and efficiently.

```java
public class House {
    private String address;

    public House(String address) {
        this.address = address;
    }
}

public class LuxuryHouse extends House {
    private int bedroomCount;

    public LuxuryHouse(String address, int bedroomCount) {
        super(address);
        this.bedroomCount = bedroomCount;
    }
}
```

**Check:** What does the `super` keyword do in the LuxuryHouse class?

Rating (1-5): 

## R04: exception_handling / analogy

Exception handling is like a safety net under a trapeze artist: if something goes wrong, the net catches the fall and the show goes on. The `try` block is the performance, the exception is the fall, and the `catch` block is the net. A `finally` block is like the cleanup crew that works after every show, whether or not anyone fell.

**Check:** What happens in this analogy if no net is set up?

Rating (1-5): 

## R05: inheritance / simplified

Inheritance means one class borrows what another class already has. The class that borrows is the child, and the class it borrows from is the parent. You write `extends` to connect them, like `class Dog extends Animal`.

**Check:** In `class Dog extends Animal`, which class is the child?

Rating (1-5): 

## R06: loops / example

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

## R07: loops / analogy

A loop is like running laps around a track: you keep going round until you have done the number of laps you planned. The lap you are on is the counter, the planned number of laps is the condition, and finishing one lap is one pass through the body. In Java, `for (int lap = 1; lap <= 3; lap++)` runs exactly three laps.

**Check:** In this analogy, what does `lap++` correspond to?

Rating (1-5): 

## R08: exception_handling / example

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

## R09: exception_handling / example

```java
public class ExceptionHandlingExample {
    public static void main(String[] args) {
        try {
            int result = 5 / 0;
        } catch (ArithmeticException e) {
            System.out.println("Caught an ArithmeticException: " + e.getMessage());
        }
    }
}
```

This example demonstrates the use of a try-catch block in Java to handle exceptions. The try block contains code that might throw an exception, and the catch block catches and handles the exception. In this case, the code tries to divide by zero, which throws an ArithmeticException, and the catch block prints an error message.

**Check:** Can you explain what the difference is between a compile-time exception and a runtime exception?

Rating (1-5): 

## R10: loops / theory

Loops in programming are used to repeat a set of instructions for a specified number of times. A loop allows you to execute a block of code multiple times without having to repeat the code itself. The key rules of loops are:

1. A loop consists of a set of instructions that are repeated until a certain condition is met.
2. There are two types of loops in Java: For-each loop and While loop.
3. A For-each loop is used to iterate over an array or collection of values.
4. A While loop continues to execute a set of instructions as long as a certain condition is true.

For example, in Java, you can use a while loop to print numbers from 1 to 10: ```java
int i = 1;
while (i <= 10) {
    System.out.println(i);
    i++;
}
```

```

**Check:** Can you explain the difference between a for-each loop and a while loop?

Rating (1-5): 

## R11: inheritance / simplified

So, you're having trouble understanding inheritance in Java? Inheritance is a way for one class to inherit properties and behavior from another class. Think of it like a child inheriting traits from their parents. The child class gets all the benefits of the parent class, but can also add new traits or change the ones they inherited.

For example, if we have a `Vehicle` class and a `Car` class, the `Car` class can inherit all the properties and behavior of the `Vehicle` class, and then add its own specific traits, like a steering wheel or engine. This way, we don't have to repeat code in the `Car` class that's already in the `Vehicle` class.

**Check:** Which step of that explanation would you like me to go over again?

Rating (1-5): 

## R12: loops / theory

A loop repeats a block of code. A `for` loop is used when you know how many times to repeat, and it has three parts: an initialiser, a condition checked before each pass, and an update run after each pass. A `while` loop repeats as long as its condition stays true, so something inside it must eventually make the condition false. Otherwise it never stops.

**Check:** How many times does the body of `for (int i = 0; i < 3; i++)` run?

Rating (1-5): 

## R13: inheritance / theory

Inheritance in Java is a concept where one class can inherit the properties and behavior of another class. The child class, also known as the subclass or derived class, inherits all the fields and methods of the parent class, also known as the superclass or base class. The child class can also add new fields and methods or override the ones inherited from the parent class. The key rules of inheritance are: the child class must have a superclass, the child class must have at least one method that is not inherited from the superclass, and the child class can have private members that are not accessible from outside the class.

```java
public class Animal {
    public void sound() {
        System.out.println("The animal makes a sound.");
    }
}

public class Dog extends Animal {
    public void sound() {
        System.out.println("The dog barks.");
    }
}
```

**Check:** What is the term for the parent class in inheritance?

Rating (1-5): 

## R14: exception_handling / simplified

When an error occurs in your Java program, it's called an exception. Think of it like a mistake that the computer finds in your code. Exception handling is a way to deal with these mistakes, so the program doesn't crash or get confused. Instead, it can try to fix the problem or show you what went wrong. In Java, you can use a special word called `try` to tell the computer to try to do something. If it finds a mistake, it will use another word called `catch` to show you what happened.

```
try {
    // code that might throw an exception
} catch (Exception e) {
    // code to deal with the exception
}
```

For example, if you try to divide a number by zero, Java will throw an exception. You can use the `catch` word to show a message saying "Can't divide by zero!".

```
try {
    int x = 10 / 0;
} catch (ArithmeticException e) {
    System.out.println("Can't divide by zero!");
}
```

**Check:** Which step of that explanation would you like me to go over again?

Rating (1-5): 

## R15: loops / example

```java
for (int i = 0; i < 5; i++) {
    System.out.println(i);
}
```

This code shows a simple `for` loop that prints the numbers 0 to 4. The loop variable `i` starts at 0 and is incremented by 1 in each iteration. The loop continues until `i` is no longer less than 5. This is a basic example of how to use a `for` loop in Java.

The `for` loop is often used for repetitive tasks like iterating over arrays or collections. It's a fundamental concept in programming and is used in many languages.

What is the difference between a `for` loop and a `while` loop in Java?

**Check:** What do you think would happen if you changed one line of this example?

Rating (1-5): 

## R16: loops / simplified

Loops in Java are used to repeat a set of instructions. Think of it like a merry-go-round that keeps going around and around. Imagine you're making a list of items you need to buy at the store. Instead of writing out the entire list over and over again, you can use a loop to repeat the item you need to buy for each item on the list.

For example, you could use a loop to print out a list of numbers from 1 to 5. You wouldn't have to write out each number individually - just tell the computer to keep printing numbers until it gets to 5.

In Java, we use the `for` loop to create these repeating cycles. It's like a recipe for the computer to follow.

```java
for (int i = 1; i <= 5; i++) {
    System.out.println(i);
}
```

This code will print out the numbers 1, 2, 3, 4, and 5, one number per line.

**Check:** Which step of that explanation would you like me to go over again?

Rating (1-5): 

## R17: inheritance / example

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

## R18: inheritance / analogy

Inheritance is like a family: a child inherits traits from a parent, such as eye colour, but can also have traits of their own. In Java the parent is the superclass and the child is the subclass, and `extends` is the family link. A `Dog` that extends `Animal` automatically has what every `Animal` has, and can add barking on top.

**Check:** In this analogy, what does a trait the child has but the parent lacks correspond to in code?

Rating (1-5): 

## R19: exception_handling / theory

An exception is an event that disrupts normal execution, such as dividing an integer by zero or reading a missing file. You wrap risky code in a `try` block and handle the problem in a `catch` block for the exception type you expect. An optional `finally` block runs whether or not an exception happened, which makes it useful for cleanup. If nothing catches an exception, the program stops with an error message.

**Check:** When does the `catch` block run?

Rating (1-5): 

## R20: exception_handling / theory

Exception handling in Java is a mechanism used to handle runtime errors and exceptions. An exception is an event that occurs during the execution of a program, which disrupts the normal flow of the program's instructions. The key goal of exception handling is to prevent the program from crashing and to provide a way to handle the exception in a controlled manner. Java provides a try-catch block mechanism to catch and handle exceptions. The try block contains the code that might throw an exception, while the catch block contains the code that will be executed when an exception is thrown.

**Check:** In your own words, what is the main idea here?

Rating (1-5): 

## R21: inheritance / example

```java
public class Animal {
    private String name;

    public Animal(String name) {
        this.name = name;
    }

    public void sound() {
        System.out.println("The animal makes a sound.");
    }
}

public class Dog extends Animal {
    public Dog(String name) {
        super(name);
    }

    public void sound() {
        System.out.println("The dog barks.");
    }
}

public class Main {
    public static void main(String[] args) {
        Dog dog = new Dog("Fido");
        dog.sound();
    }
}
```

This example shows inheritance in Java, where the `Dog` class extends the `Animal` class, inheriting its properties and methods. The `Dog` class also adds its own specific method, `sound()`, which overrides the one from the `Animal` class.

**Check:** Can you explain the difference between `public` and `private` access modifiers in Java?

Rating (1-5): 

## R22: exception_handling / simplified

An exception is Java's way of saying that something went wrong while the program was running. With `try`, you say "attempt this". With `catch`, you say "if that went wrong, do this instead".

**Check:** Which keyword holds the code that might fail?

Rating (1-5): 

## R23: exception_handling / analogy

Exception handling is like trying to catch a ball that someone has dropped. Imagine you're standing near a park and someone throws a ball in your direction. You want to catch the ball before it hits the ground. If you're standing close enough, you can catch it, but if you're too far away, the ball will hit the ground before you can react. In Java, the ball represents the code that's running, and the ground represents an error or unexpected situation. The "catch" part represents the exception handling mechanism, which helps you deal with these unexpected situations by giving you a chance to handle the error instead of letting it crash the program. When an exception is thrown, Java will look for a block of code that's specifically designed to handle that type of exception, just like how you would look for someone in the park who can catch the ball for you.

**Check:** How would you map this comparison back to the Java code?

Rating (1-5): 

## R24: loops / analogy

Loops are like driving on the highway. Imagine you're on a long road trip, and you need to visit a certain number of cities. You can't just go to each city one by one, that would take too long. Instead, you can drive to a certain distance, say 100 miles, and then stop. You do this multiple times, and each time you stop, you get closer to your destination.

In Java, we use the `for` loop to drive to a certain distance (the number of iterations), and then we do something inside the loop, like visit a city. The loop keeps going until we reach our destination, or we decide to stop.

```java
for (int i = 0; i < 10; i++) {
    System.out.println("Visiting city " + (i + 1));
}
```

**Check:** Can you explain what a `break` statement does in a loop?

Rating (1-5): 
