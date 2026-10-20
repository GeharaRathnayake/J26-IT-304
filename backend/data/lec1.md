---
source: lec1.pdf
course: Object Oriented Programming (SLIIT - Faculty of Computing)
lecture_id: lec1        # suggested tag, change to match your taxonomy
module_id: module1      # suggested tag, change to match your taxonomy
slides: 9-50
conversion: image-only content converted to text, slide numbers kept; code that was cut off on the slide or incomplete was completed or corrected and marked with [completed], [reconstructed] or [corrected] notes; all code blocks on slides 27, 35-38, 40-46 were compiled and run
---

## Slide 9
Learning Outcomes
At the end of the Lecture students should be able to
- List the differences between C++ and Java
- List how a Java program is compiled and executed in a Computer.
- List Features that make Java unique
- Write, Compile and Execute simple Java programs
- Write a Java program including
  - Input / output commands
  - Variable
  - Sequence
  - Selection
  - Repetition

## Slide 10
Java
- 1991 - James Gosling, Sun Microsystems, Inc.
- Originally a platform independent language for programming home appliances and was called "Oak" later renamed "Java" in 1995.
- Later (1994) used for World Wide Web applications (since byte code can be downloaded and run without compiling it)
- Eventually used as a general-purpose programming language (for the same reason as above plus it is object-oriented)
- Why the name "Java"? Java was then named "Java", paying homage to the large amounts of coffee consumed by the team.
- Now owns by Oracle

[Image: portrait photo of a man next to the Java logo]

## Slide 11
Java
[Image: Java logo]
- Full-fledged application programming language
- Additional capability as a Web programming language (currently the strength of its application base)
- A pure OO programming language
- NOT radical or especially new
- Adopts its looks from C++, and its behavior from Smalltalk
- Compiled to processor-neutral instruction set then interpreted on each supporting platform
- Extremely fast adoption rate! (due to WWW)

## Slide 12
Java Buzzwords
[Image: Java logo]
[Table: Java buzzword and its meaning]

| Buzzword | Meaning |
|---|---|
| Simple | Java has a concise, cohesive set of features that makes it easy to learn and use. |
| Secure | Java provides a secure means of creating Internet applications. |
| Portable | Java programs can execute in any environment for which there is a Java run-time system. |
| Object-oriented | Java embodies the modern, object-oriented programming philosophy. |
| Robust | Java encourages error-free programming by being strictly typed and performing run-time checks. |
| Multithreaded | Java provides integrated support for multithreaded programming. |
| Architecture-neutral | Java is not tied to a specific machine or operating system architecture. |
| Interpreted | Java supports cross-platform code through the use of Java bytecode. |
| High performance | The Java bytecode is highly optimized for speed of execution. |
| Distributed | Java was designed with the distributed environment of the Internet in mind. |
| Dynamic | Java programs carry with them substantial amounts of run-time type information that is used to verify and resolve accesses to objects at run time. |

## Slide 13
Java Terminology
[Image: Java logo]
- Class - A collection of data and methods that operate on that data.
- Method - A group of statements in a class that handle a task.
- Attribute - A property of an instance of a class.
- Interface - A skeleton class.
- Package - A group of logically related codes (classes & interfaces).

## Slide 14
Java Terminology
[Image: Java logo]
- Bytecodes
  - A set of instructions that look like machine code, but are not specific to any processor.
- Virtual Machine
  - The environment in which Java runs. The JVM is responsible for executing the bytecodes and has responsibility for the fundamental capabilities of Java.

## Slide 15
C++ vs Java
[Diagram: two code boxes side by side. Left box is the C++ program, right box is the Java program. Below them, an output box showing "Hello World !". The file names Helloworld.cpp (left) and Helloworld.java (right) are shown in black labels.]

C++ (Helloworld.cpp):
```cpp
// C++ Program
#include <iostream>

int main ( )
{
  std::cout << "Hello World !" <<
                     std::endl;

  return 0;
}
```

Java (Helloworld.java):
```java
// Java Program

public class Helloworld {
  public static void main(String
        args[]) {
     System.out.println(
          "Hello World !");
  }
}
```
Output : Hello World !

## Slide 16
First Java Program
```java
/* First Java Program
*/

public class HelloWorld {
  public static void main(String args[]) {
    System.out.println("Hello World !");
  }
}
```

## Slide 17
Comments
```java
// Java Program : prg_01.java
// Printing a String
```
- Comments provide information to the people who read the program
- Comments are removed by the preprocessor, therefore the compiler ignores them
- In Java, there are two types of comments
  - Single line comments //
  - Delimited comments /* */ for comments with more than one line.

## Slide 18
Everything is Object Oriented
```java
public class HelloWorld
```
- In Java is fully object oriented, even the simplest program needs to be written using a class.
- HelloWorld is the name of the class.
- A public class needs to be stored in a file name that matches the class name. i.e. The above code needs to be saved in a filename called HelloWorld.java

## Slide 19
The main method
```java
public static void main(String[] args)
```
- Java programs begin executing at method main. The main method must be given as above.
- The main method is one of the methods in a class
- void methods do not return a value.

## Slide 20
Output Statement
```java
System.out.println("Hello World !");
```
- Instructs the computer to display the data within brackets to the screen.
- "Hello World !" : String / String Literal. What you need to display on screen
- System.out.println() moves the cursor to the next line after displaying the data

## Slide 21
Exercise - 1
- Write a Java program to display your name and address in 3 lines.

## Slide 22
Java Keywords
[Table: Java keywords in 5 columns]

| | | | | |
|---|---|---|---|---|
| abstract | continue | for | new | switch |
| assert | default | goto | package | synchronized |
| boolean | do | if | private | this |
| break | double | implements | protected | throw |
| byte | else | import | public | throws |
| case | enum | instanceof | return | transient |
| catch | extends | int | short | try |
| char | final | interface | static | void |
| class | finally | long | strictfp | volatile |
| const | float | native | super | while |

## Slide 23
Java Development Environment
1. Install the Java JDK. The latest Java SE JDK is 9. We will use Java SE JDK 8 in this course.
2. Editing a program
   - Type a Java program ( source code )
   - e.g :
     - vi editor ( Linux )
     - notepad ( Windows DOS prompt )
     - IDE (Eclipse, IntelliJ )
   - Extension : .java
[lecture note: the JDK versions named on this slide are those of the lecture material.]

## Slide 24
Java Development Environment cont...
3. Compiling a Java program
   - The java compiler (javac) compiles java code to an intermediate language called Java Byte Code. This is a platform neutral low level language which can be translated to machine code. Compiled java programs are stored in files with the extension .class

4. Running a Java Program
   - The java interpreter is used to run a compiled program on your computer. Each platform has its own Java Virtual Machine which translates Java Bytecode to machine code.

## Slide 25
Integrated Development Environments ( IDEs )
- Provides tools that support the software development process
- Includes, editors for writing & editing programs, debuggers for locating logical errors, design tools etc....
  - Eclipse
  - IntelliJ

## Slide 26
Java Architecture
[Diagram: four stacked boxes, top to bottom, with dashed lines between the first and second, and between the second and third:]
1. JAVA Application (Bytecodes)
2. JAVA Virtual Machine
3. Any Operating System
4. Any Hardware Platform

## Slide 27
Platform Independence
[Diagram: three stages left to right. "Java source" -> "Java compile" (arrow) -> "Java bytecode" (puzzle piece icon).]

Java source:
```java
class HelloWorld {
public static void main
(String args[]){
System.out.println("Hello World");
}
}
```
[corrected: the slide shows "Main" with a capital M and only one closing brace. Java's entry point is lowercase main, and the class needs its own closing brace, so both were corrected. Verified to compile and run.]
Java compile: javac HelloWorld.java
Java bytecode: HelloWorld.class - Platform Neutral

- Write application once, runs on any
- Written in software - defined by Oracle. Assured through compatibility test suite
- Virtual Machine - spec of microprocessor

Vendors Port VM to:
- Operating Systems
- Enable in Browsers

Java source compiled into intermediary bytecode
- Application runs anywhere Java VM is ported
- Applet runs in any Java enabled browser

[Diagram: "Interpret" and "Translate" arrows from the Virtual Machine to puzzle pieces labelled AIX / OS/400 / MVS, OS/2, Windows / Mac / Unix, and Netscape / Web Explore / Inter Explore]

## Slide 28
Java's magic Byte Code
- Generated by Java compiler
  - Instead of generating machine language as most compilers do, the Java compiler generates byte code.
- Easily translated to machine language of various kinds of computers
- Executed by Java interpreter
- Invisible to programmer
  - You don't have to know anything about how byte code works to write a Java program.

## Slide 29
Language Translation
A source program is the one that you write in the Java language and that always has a file extension of .java.

An object program is the binary byte-code program generated by the Java compiler, which always has a file extension of .class.

The .class file generated by the Java compiler contains bytecode which is a low-level code similar to machine language, but generic and not specific to any particular CPU.

## Slide 30
Java Virtual Machine
A given computer must have its own Java interpreter as part of a Java Virtual Machine, or JVM, to translate the generic bytecode into machine language for that CPU.

Virtual Machine (VM) interprets bytecodes into native machine language and runs it. Different VM exists for different computers, since bytecode does not correspond to a real machine.

## Slide 31
Why Use Byte Code?
Disadvantages:
- Requires both compiler and interpreter
- Slower program execution

Advantages:
- Portability
  - Very important
  - Same program can run on computers of different types (useful with the Internet)
- Small in size
  - Linking at runtime
  - Easy to exchange over a network

## Slide 32
Java Program Patterns
- Stand Alone Applications
  - Java programs which run in command console
  - Applications with GUI (awt/swing)
- Web-based Java Applications
  - Applets
    - Dynamic and interactive programs that can run inside a web page displayed by a browser enabled for Java
  - Servlets
    - Programs that run inside request/response oriented servers
  - JavaServer Pages
    - An extension to the servlet architecture. Allow for the separation of the display of web content and the generation of that content

## Slide 33
J.... confusion
- JVM (Java Virtual Machine )
  - JVM is a part of both the JDK and JRE that translates Java byte codes and executes them as native code on the client machine.
- JRE (Java Runtime Environment )
  - It is the environment provided for the java programs to get executed. It contains a JVM, class libraries, and other supporting files. It does not contain any development tools such as compiler, debugger, etc.
- JDK (Java Development Kit)
  - JDK contains tools needed to develop the Java programs (javac, java, javadoc, appletviewer,jdb, javap, rmic....),and a JRE to run the programs.
- Java SDK (Java software development kit)
  - SDK comprises a JDK and extra software, such as application servers, debuggers, and documentation.
- Java SE
  - Java Platform, Standard Edition (Java SE) lets you develop and deploy Java applications on desktops and servers (Same as SDK)
- J2SE, J2ME, J2EE
  - Any Java edition from 1.2 to 1.5
[lecture note: this slide reflects the Java versions and terminology used in the lecture material.]

## Slide 34
Exercise 01
What is the meaning of "write once, run anywhere"? Select the correct options:
1. Java code can be written by one team member and executed by other team members.
2. It is for marketing purposes only.
3. It enables Java programs to be compiled once and can be executed by any JVM without recompilation.
4. Old Java code doesn't need recompilation when newer versions of JVMs are released.

## Slide 35
Printing Values
- System.out.println() and System.out.print()
```java
public class Print1 {

    public static void main(String args[]) {
        System.out.print("This is line 1");
        System.out.print(" still line 1");
        System.out.println(" lets move to the next line ");
        System.out.println("finally line 2");
    }
}
```
[completed: the slide cuts off after the last println. The closing braces of main and the class were added. Verified to compile and run.]
File: Print1.java

## Slide 36
Printing Values
- System.out.println() and System.out.print()
```java
public class Print2 {
    public static void main(String args[]) {
        int no = 50;
        long population = 70000000;
        double salary = 4500.34;
        float rate = 34.5f;

        System.out.println("no = " + no);
        System.out.println("population = " + population);
        System.out.println("salary = " + salary);
        System.out.println("rate = " + rate);
    }
}
```
[completed: the slide shows only these statements. The class and main method wrapper was added so the program is whole. Verified to compile and run.]
File: Print2.java

## Slide 37
Printing Values
- System.out.println() and System.out.print()
```java
public class Print3 {
    public static void main(String args[]) {
        int no = 50;
        long population = 70000000;
        double salary = 4500.34;
        float rate = 34.5f;

        System.out.println("no = " + no + "\n"
                + "population = " + population + "\n"
                + "salary = " + salary + "\n"
                + "rate = " + rate);
    }
}
```
[completed: the slide shows only these statements. The class and main method wrapper was added so the program is whole. Verified to compile and run.]
File: Print3.java

## Slide 38
Inputing Values from the Keyboard
- Using java.util.Scanner
```java
import java.util.Scanner;

public class Input {
    public static void main(String args[]) {
        String name;
        int age;
        float salary;
        Scanner myScanner  = new Scanner(System.in);
        System.out.print("Enter your name : ");
        name = myScanner.next();
        System.out.print("Enter your age : ");
        age = myScanner.nextInt();
        System.out.print("Enter your salary : ");
        salary = myScanner.nextFloat();

        System.out.println("Name = " + name);
        System.out.println("Age = " + age);
        System.out.println("Salary = " + salary);
    }
}
```
[reconstructed: the slide is cut off after the line printing Name. The Age and Salary println lines and the closing braces were added by following the pattern of the input lines. The exact wording of the hidden lines is not visible on the slide. Verified to compile and run.]
File: Input.java
(The slide shows editor line numbers 3 to 18 beside this code.)

## Slide 39
Java vs C++ Language
- Java control structures are identical in syntax
  - selection - if, switch,
  - Repetition - while, do while, for
- Within a method the major difference is the print commands and the input commands.
- The basic data types integers and float are used in the same way. There is a separate data type in Java for string data called String.
- Calculations are also identical.
- There is a slight difference on how arrays are declared (i.e. similar to C++ dynamic arrays)

## Slide 40
Use of Variables
- Same as in C++ (See Variables.cpp)
```java
public class Variables {
    public static void main(String args[]) {
        int no = 50;
        long population = 70000000;
        double salary = 4500.34;
        float rate = 34.5f;

        System.out.println(no);
        System.out.println(population);
        System.out.println(salary);
        System.out.println(rate);
    }
}
```
[completed: the slide cuts off after the last println. The closing braces of main and the class were added. Verified to compile and run.]
File: Variables.java

## Slide 41
Calculations
- Same as in C++ (Calculations.cpp)
```java
public class Calculations {
    public static void main(String args[]) {
        int no = 50;
        long population = 70000000;
        double salary = 4500.34;
        float radius = 30.0f;

        int remainder = no % 3;
        double contribution = population * 100;
        double area = 22.0/7*radius*radius;
    }
}
```
[completed: the slide shows only these statements. The class and main method wrapper was added so the program is whole. Verified to compile and run.]
File: Calculations.java

## Slide 42
Selection - If
- Same as in C++
```java
public class If {
    public static void main(String args[]) {
        int opt;
        System.out.println("1. Malabe Campus");
        System.out.println("2. Metro Campus");
        System.out.println("3. Matara Centre");
        System.out.println("4. Kandy Centre");
        System.out.println("5. Kurunagala");
        System.out.println("6. Jaffna");
        System.out.println("0. Exit");

        opt = 5;
        System.out.print("Option : ");
        System.out.println(opt);

        if (opt == 1)
            System.out.println("Malabe Campus");
        else if (opt == 2)
            System.out.println("Metro Campus");
        else if (opt == 3)
            System.out.println("Matara Centre");
        else if (opt == 4)
            System.out.println("Kandy Centre");
        else if (opt == 5)
            System.out.println("Kurunagala");
        else if (opt == 6)
            System.out.println("Jaffna");
        else if (opt == 0)
            System.out.println("Exit");
        else
            System.out.println("Invalid option");
    }
}
```
[reconstructed: the slide shows only the last menu lines and part of the if chain, and is cut off at the branch for option 4. Added: the int opt declaration, the wrapper, menu lines 1-4 (using the campus names from the branches), the branch for option 4 (the hidden line appears to print Kandy Centre), and branches for 5, 6, 0 and an else. The exact wording of the hidden lines is not visible on the slide. Verified to compile and run.]
File: If.java

## Slide 43
Selection - Switch
- Same as in C++
```java
public class Switch {
    public static void main(String args[]) {
        int opt;
        System.out.println("1. Malabe Campus");
        System.out.println("2. Metro Campus");
        System.out.println("3. Matara Centre");
        System.out.println("4. Kandy Centre");
        System.out.println("5. Kurunagala");
        System.out.println("6. Jaffna");
        System.out.println("0. Exit");

        opt = -5;
        System.out.print("Option : ");
        System.out.println(opt);
        switch (opt) {
            case 1 : System.out.println("Malabe Campus");
                     break;
            case 2 : System.out.println("Metro Campus");
                     break;
            case 3 : System.out.println("Matara Centre");
                     break;
            case 4 : System.out.println("Kandy Centre");
                     break;
            case 5 : System.out.println("Kurunagala");
                     break;
            case 6 : System.out.println("Jaffna");
                     break;
            case 0 : System.out.println("Exit");
                     break;
            default : System.out.println("Invalid option");
        }
    }
}
```
[reconstructed: the slide is cut off after case 3. Added: the int opt declaration, the wrapper, menu lines 1-4, cases 4, 5, 6, 0 and a default case. The exact wording of the hidden lines is not visible on the slide. Verified to compile and run.]
File: Switch.java

## Slide 44
Repetition - while
- Same as in C++
```java
public class While {
    public static void main(String args[]) {
        int r = 1;
        while (r < 100) {
            System.out.println(r);
            r++;
        }
        System.out.println();
        r = 50;
        while (r > 0) {
            System.out.print(r + " ");
            r -= 5;
        }
    }
}
```
[completed: the slide shows only these statements. The class and main method wrapper was added so the program is whole. Verified to compile and run.]
File: While.java

## Slide 45
Repetition - for
- Same as in C++
```java
public class For {
    public static void main(String args[]) {
        for (int r = 1; r<100; r++) {
            System.out.println(r);
        }
        System.out.println();
        for (int r = 50; r > 0; r-=5) {
            System.out.print(r + " ");
        }
    }
}
```
[completed: the slide shows only these statements. The class and main method wrapper was added so the program is whole. Verified to compile and run.]
File: For.java

## Slide 46
Repetition - do while
- Same as in C++
```java
public class DoWhile {
    public static void main(String args[]) {
        int r = 1;
        do {
            System.out.println(r);
            r++;
        } while (r < 100);
        System.out.println();
        r = 50;
        do {
            System.out.print(r + " ");
            r -= 5;
        } while (r > 0);
    }
}
```
[completed: the slide shows only these statements. The class and main method wrapper was added so the program is whole. Verified to compile and run.]
File: DoWhile.java

## Slide 47
Exercise - 2
- Write a C++ program to input the length and the width of a rectangle and calculate and print the perimeter.

## Slide 48
Exercise - 3
- Write a program to input 3 integers and print the largest and the smallest of the 3 numbers entered.

## Slide 49
Exercise - 4
- Write a program to input 10 numbers from the keyboard and find how many odd numbers and how many even numbers were entered.

## Slide 50
Thank you!
