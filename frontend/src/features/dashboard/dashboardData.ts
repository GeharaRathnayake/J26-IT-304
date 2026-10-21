import type { WeakTopicItem, TeachingMethodCard, StudentDashboardProfile } from './types';

export const initialProfile: StudentDashboardProfile = {
  name: 'Demo',
  role: 'Student',
  avatarLetter: 'D',
  statusText: 'Logged in',
  currentLevel: 'Normal',
  levelBadge: 'Lvl 2 Intermediate',
  levelProgressPercent: 65,
  conceptsLearned: 14,
  totalConceptsInCurriculum: 28,
  weakTopicsCount: 3,
  topHelpfulStyle: 'analogy',
  topHelpfulStyleName: 'Analogy',
  topHelpfulStyleSuccessRate: 88,
  studyStreakDays: 5,
  totalTutoringMinutes: 142,
  vapiEngineStatus: 'ready',
  llmModelName: 'llama3.2:3b (Ollama)',
};

export const initialTeachingMethods: TeachingMethodCard[] = [
  {
    strategy: 'analogy',
    name: 'Real-World Analogy & Mental Models',
    shortLabel: 'Analogy',
    tagline: 'Anchors abstract JVM & memory mechanics to intuitive physical objects',
    rank: 1,
    isTopRecommendation: true,
    successRate: 88,
    winCount: 14,
    totalUses: 16,
    avgResolutionTimeMinutes: 1.4,
    badge: 'ðŸ† #1 Top Personalized Match',
    whyItWorks:
      'Your learning telemetry shows highest concept retention when abstract Java constructs (heap references, inheritance hierarchies, runtime dispatch) are mapped to familiar physical systems before inspecting raw syntax.',
    cognitiveProfileMatch: '94% affinity with analogical and spatial mental models',
    bestFitScenarios: [
      'Heap vs Stack memory allocation',
      'Class blueprints vs Object instances',
      'Polymorphic method resolution (Dynamic Dispatch)',
      'Interface contracts vs Concrete implementations',
    ],
    colorTheme: {
      gradient: 'from-emerald-500 to-teal-600',
      badgeBg: 'bg-emerald-500/10 text-emerald-700 border-emerald-300',
      badgeText: 'text-emerald-700',
      border: 'border-emerald-500/40 hover:border-emerald-500',
      accent: 'emerald',
      glow: 'shadow-emerald-500/10',
    },
  },
  {
    strategy: 'example',
    name: 'Step-by-Step Code Deconstruction',
    shortLabel: 'Code Example',
    tagline: 'Annotated, runnable code snippets with live variable tracking',
    rank: 2,
    isTopRecommendation: false,
    successRate: 76,
    winCount: 11,
    totalUses: 14,
    avgResolutionTimeMinutes: 2.1,
    badge: 'âš¡ #2 Practical Reinforcement',
    whyItWorks:
      'Provides practical code scaffolds that immediately prove compile-time and runtime behavior. You grasp syntax subtleties and control flow fastest when stepping through small, focused code blocks.',
    cognitiveProfileMatch: '82% affinity with concrete code demonstration',
    bestFitScenarios: [
      'try-catch-finally execution flow & return statements',
      'Method overloading vs overriding syntactical signatures',
      'Array manipulation and loop boundary conditions',
      'Custom exception definitions',
    ],
    colorTheme: {
      gradient: 'from-sky-500 to-blue-600',
      badgeBg: 'bg-sky-500/10 text-sky-700 border-sky-300',
      badgeText: 'text-sky-700',
      border: 'border-sky-500/30 hover:border-sky-500',
      accent: 'sky',
      glow: 'shadow-sky-500/10',
    },
  },
  {
    strategy: 'simplified',
    name: 'Single-Concept Deconstruction',
    shortLabel: 'Simpler Version',
    tagline: 'Strips out heavy technical jargon and isolates single operational rules',
    rank: 3,
    isTopRecommendation: false,
    successRate: 62,
    winCount: 8,
    totalUses: 13,
    avgResolutionTimeMinutes: 2.9,
    badge: 'ðŸ§© #3 Cognitive Load Reducer',
    whyItWorks:
      'Reduces working memory strain by breaking multi-clause definitions into 1-2 bullet rules with minimal terminology. Effective when cognitive overload is detected after failed theoretical turns.',
    cognitiveProfileMatch: '68% affinity when working memory is overloaded',
    bestFitScenarios: [
      'Base cases and stack frame unwinding in recursion',
      'Access modifiers hierarchy (private -> default -> protected -> public)',
      'Primitive vs Reference type value-copy behavior',
    ],
    colorTheme: {
      gradient: 'from-amber-500 to-orange-600',
      badgeBg: 'bg-amber-500/10 text-amber-700 border-amber-300',
      badgeText: 'text-amber-700',
      border: 'border-amber-500/30 hover:border-amber-500',
      accent: 'amber',
      glow: 'shadow-amber-500/10',
    },
  },
  {
    strategy: 'theory',
    name: 'Formal Theory & Java Language Specs',
    shortLabel: 'Theory',
    tagline: 'Formal definitions, JVM type systems, and academic terminology',
    rank: 4,
    isTopRecommendation: false,
    successRate: 38,
    winCount: 5,
    totalUses: 13,
    avgResolutionTimeMinutes: 4.5,
    badge: 'ðŸ“š #4 Foundational Reference',
    whyItWorks:
      'Essential for academic examinations and formal JLS compliance, but your telemetry shows it often triggers confusion when introduced as the initial explanation for unfamiliar topics.',
    cognitiveProfileMatch: '45% initial comprehension rate when used alone',
    bestFitScenarios: [
      'Formal exam definitions and Java Language Specifications',
      'Theoretical memory architecture (Method Area, Heap, Thread Stacks)',
      'Object-Oriented design principles (SOLID guidelines)',
    ],
    colorTheme: {
      gradient: 'from-purple-500 to-indigo-600',
      badgeBg: 'bg-purple-500/10 text-purple-700 border-purple-300',
      badgeText: 'text-purple-700',
      border: 'border-purple-500/30 hover:border-purple-500',
      accent: 'purple',
      glow: 'shadow-purple-500/10',
    },
  },
];

export const initialWeakTopics: WeakTopicItem[] = [
  {
    id: 'weak-1',
    slug: 'classes_and_objects',
    title: 'Object & Class',
    category: 'Object-Oriented Programming',
    severity: 'critical',
    status: 'weak',
    cyclesNeeded: 3,
    lastEncountered: 'Today, 2:40 PM',
    masteryScore: 32,
    cognitiveBlocker:
      'Confuses the class definition (blueprint in bytecode/method area) with instantiated objects living in Heap memory. Tries to access instance fields without instantiating `new`, or assumes modifying one object changes other instances.',
    detectedMisconception:
      'Mental model gap: Treating Class and Object as synonymous entities rather than template vs active memory allocation.',
    commonCompilerOrLogicError:
      'Non-static field cannot be referenced from a static context',
    recommendedMethod: 'analogy',
    recommendedMethodReason:
      'Analogies like "Architectural Blueprint vs Built Houses" or "Cookie Cutter vs Baked Cookies" consistently trigger immediate breakthrough.',
    strategiesAttempted: [
      {
        strategy: 'theory',
        strategyLabel: 'Theory',
        outcome: 'confused',
        timestamp: 'Turn 1 (14:32)',
        tutorExcerpt:
          'A class is a user-defined blueprint prototype from which objects are instantiated, encapsulating state representations and behavioral routines.',
        studentResponse:
          '"Wait, so if I create a class Car, is that already a car I can drive in the code?"',
      },
      {
        strategy: 'example',
        strategyLabel: 'Code Example',
        outcome: 'confused',
        timestamp: 'Turn 2 (14:34)',
        tutorExcerpt:
          'Look at this: `Car myCar = new Car();` creates the instance, whereas `class Car { String color; }` is just the type definition.',
        studentResponse:
          '"I still get confused about why Car.color gives an error but myCar.color works."',
      },
      {
        strategy: 'simplified',
        strategyLabel: 'Simpler Version',
        outcome: 'confused',
        timestamp: 'Turn 3 (14:36)',
        tutorExcerpt:
          'Rule 1: Class = The recipe.\nRule 2: Object = The actual cake made from that recipe.',
        studentResponse:
          '"Still not 100% sure how references work when passing them."',
      },
      {
        strategy: 'analogy',
        strategyLabel: 'Analogy',
        outcome: 'breakthrough',
        timestamp: 'Turn 4 (14:38)',
        tutorExcerpt:
          'Think of an architectural blueprint for a house. The blueprint is on paper â€” you cannot sleep in it or paint its walls. Only when construction workers build a physical house (using `new House()`) do you have real walls to paint! If you build two houses from the same blueprint, painting House #1 red does NOT turn House #2 red.',
        studentResponse:
          '"Ohhh! That makes total sense! The class is the blueprint and new House() is the actual physical house!"',
      },
    ],
    explanationSamples: {
      analogy: {
        strategy: 'analogy',
        title: 'Real-World Analogy: Blueprint vs Physical House',
        subtitle: 'Highest student breakthrough rate (88%)',
        content:
          'Think of a **Class** as an architect\'s architectural blueprint, and an **Object** as the actual house built from that blueprint.\n\nâ€¢ The **Blueprint** (`class House`) specifies how many rooms and windows exist, but nobody can live inside paper drawings.\nâ€¢ When you type `new House()`, the construction crew builds a **real physical house** on a plot of land (Heap memory).\nâ€¢ If you build 10 houses from 1 blueprint, painting the door of House #1 red **does not** turn the other 9 doors red. Each object holds its own independent state!',
        codeSnippet: `// The Blueprint (Class)
class House {
    String doorColor; // Each house has its own door color
}

// Building two distinct houses (Objects in Heap)
House house1 = new House();
House house2 = new House();

house1.doorColor = "Red";   // Only house1 changes
house2.doorColor = "Blue";  // house2 remains Blue!`,
      },
      example: {
        strategy: 'example',
        title: 'Concrete Code Walkthrough',
        subtitle: 'Syntax & memory pointers',
        content:
          'Here is how Java allocates an object in memory step-by-step using the `new` keyword and reference assignment.',
        codeSnippet: `// 1. Blueprint definition
public class Student {
    String name;
    int id;
}

public class Main {
    public static void main(String[] args) {
        // 2. Declaration creates reference variable on Stack
        Student s1; 
        
        // 3. 'new' allocates memory block on Heap & returns address
        s1 = new Student();
        s1.name = "Alice";
        
        System.out.println(s1.name); // Outputs: Alice
    }
}`,
      },
      simplified: {
        strategy: 'simplified',
        title: 'Core Rules (Zero Jargon)',
        subtitle: '3 Golden rules to remember',
        content:
          '1. **Class = Recipe.** It only describes ingredients and steps.\n2. **Object = The Meal.** You cannot eat the recipe card; you eat the cooked meal.\n3. **`new` Keyword = The Cooking Action.** Without `new`, you have no meal in your hands.',
      },
      theory: {
        strategy: 'theory',
        title: 'Formal Academic Definition (JLS)',
        subtitle: 'Java Language Specification Â§8.1',
        content:
          'A class is a reference type declaration that defines a template for creating objects. It encapsulates data members (fields) representing state and member methods providing executable operations. An object is an instantiated entity possessing identity, state, and behavior, resident within the JVM garbage-collected heap.',
      },
    },
    practiceQuestion: {
      question:
        'Which statement correctly describes what happens when executing: `Car c1 = new Car(); Car c2 = new Car(); c1.speed = 50;`?',
      options: [
        'Both c1 and c2 will have speed = 50 because they share the same class definition.',
        'Only c1 has speed = 50. c2 has default speed = 0 because each instance has its own memory in the Heap.',
        'A compiler error occurs because speed cannot be modified after object creation.',
        'The Class object itself is permanently mutated.',
      ],
      correctIndex: 1,
      explanation:
        'Objects created with `new` have separate memory allocations in the Heap. Mutating an instance variable on `c1` has zero effect on `c2`.',
    },
  },
  {
    id: 'weak-2',
    slug: 'polymorphism',
    title: 'Polymorphism & Dynamic Dispatch',
    category: 'Object-Oriented Programming',
    severity: 'moderate',
    status: 'weak',
    cyclesNeeded: 3,
    lastEncountered: 'Yesterday, 5:15 PM',
    masteryScore: 48,
    cognitiveBlocker:
      'Struggles with the difference between the Reference Type (compile-time boundary) and the Actual Object Type (runtime execution). Confuses method overloading with dynamic method overriding.',
    detectedMisconception:
      'Believing that calling a method via a superclass reference invokes the superclass implementation rather than the overridden subclass version.',
    commonCompilerOrLogicError:
      'Cannot find symbol (trying to invoke subclass-specific method via superclass reference)',
    recommendedMethod: 'analogy',
    recommendedMethodReason:
      'Universal remote control analogy makes compile-time button layout vs runtime target appliance crystal clear.',
    strategiesAttempted: [
      {
        strategy: 'theory',
        strategyLabel: 'Theory',
        outcome: 'confused',
        timestamp: 'Turn 1',
        tutorExcerpt:
          'Polymorphism allows objects of different concrete classes to be treated as instances of a common superclass, dynamically binding the virtual method table at runtime.',
        studentResponse:
          '"If it is treated as the superclass, why does the subclass method run instead?"',
      },
      {
        strategy: 'example',
        strategyLabel: 'Code Example',
        outcome: 'confused',
        timestamp: 'Turn 2',
        tutorExcerpt:
          '`Animal a = new Dog(); a.makeSound();` will print "Woof!" instead of "Generic sound".',
        studentResponse:
          '"Why declare it as Animal if it is a Dog? That just seems redundant."',
      },
      {
        strategy: 'analogy',
        strategyLabel: 'Analogy',
        outcome: 'breakthrough',
        timestamp: 'Turn 3',
        tutorExcerpt:
          'Think of a Universal Remote Control. The buttons on the remote represent the Reference Type (`Animal`). The remote has a "Play" button. When pointed at a DVD player, it spins a disk. When pointed at a Netflix box, it streams over Wi-Fi. The controller doesn\'t need to know the internal electronics of the Netflix box; it only presses "Play", and the device itself decides how to respond!',
        studentResponse:
          '"Now I get it! The reference is the remote control buttons, and the object is the actual device responding!"',
      },
    ],
    explanationSamples: {
      analogy: {
        strategy: 'analogy',
        title: 'Real-World Analogy: The Universal Remote Control',
        subtitle: 'Reference vs Execution',
        content:
          'Think of **Reference Type** as the buttons on a universal remote, and **Object Type** as the device receiving the signal:\n\nâ€¢ The remote label says `Animal`. It only has buttons for actions every animal can do (`makeSound()`, `eat()`).\nâ€¢ At runtime, the remote is paired with a `Dog` object.\nâ€¢ You press `makeSound()`. The `Dog` hears the command and barks ("Woof!"). You didn\'t have to buy a special "Dog Remote"!\nâ€¢ But you cannot press a "fetchBall()" button because a general Animal remote does not have that button!',
      },
      example: {
        strategy: 'example',
        title: 'Polymorphic Dispatch Example',
        subtitle: 'Superclass reference to Subclass instance',
        content: 'Observe how the JVM decides which method to run at runtime:',
        codeSnippet: `class Animal {
    void speak() { System.out.println("Animal sound"); }
}

class Dog extends Animal {
    @Override
    void speak() { System.out.println("Woof!"); }
    void wagTail() { System.out.println("Wagging..."); }
}

public class Main {
    public static void main(String[] args) {
        Animal pet = new Dog(); // Animal reference, Dog object
        
        pet.speak(); // Prints "Woof!" (Dynamic Dispatch!)
        
        // pet.wagTail(); // COMPILE ERROR: Animal reference has no wagTail()!
    }
}`,
      },
      simplified: {
        strategy: 'simplified',
        title: '2 Simple Rules for Polymorphism',
        subtitle: 'Compile-Time vs Runtime',
        content:
          '1. **Compiler check:** Looks at the LEFT side (`Animal`). Can only call methods declared in `Animal`.\n2. **Runtime execution:** Looks at the RIGHT side (`new Dog()`). Runs the actual version defined in `Dog`.',
      },
      theory: {
        strategy: 'theory',
        title: 'Dynamic Method Dispatch Specification',
        subtitle: 'JVM Invokevirtual Bytecode Instruction',
        content:
          'Dynamic method dispatch is the mechanism by which a call to an overridden method is resolved at runtime rather than compile time. The JVM uses the `invokevirtual` instruction to inspect the `vtable` of the receiver object at runtime to locate the concrete implementation.',
      },
    },
    practiceQuestion: {
      question:
        'Given: `Shape s = new Circle();` where `Circle` overrides `draw()` in `Shape`. What happens when `s.draw()` is invoked?',
      options: [
        'Shape\'s draw() runs because the variable type is Shape.',
        'Circle\'s draw() runs because runtime dispatch targets the actual object.',
        'A compile error occurs unless you cast `(Circle) s`.',
        'Both methods run sequentially.',
      ],
      correctIndex: 1,
      explanation:
        'Dynamic dispatch always routes to the overriding method on the concrete object instantiated on the Heap.',
    },
  },
  {
    id: 'weak-3',
    slug: 'exception_handling',
    title: 'Exception Handling: try-catch-finally',
    category: 'Core Java Mechanics',
    severity: 'moderate',
    status: 'weak',
    cyclesNeeded: 3,
    lastEncountered: '2 days ago',
    masteryScore: 54,
    cognitiveBlocker:
      'Believes that executing a `return` statement inside a `try` or `catch` block terminates execution immediately and skips the `finally` block.',
    detectedMisconception:
      'Assuming `return` immediately exits the method without executing `finally`.',
    commonCompilerOrLogicError:
      'Resource leaks / Unclosed Streams caused by misplaced cleanup code',
    recommendedMethod: 'example',
    recommendedMethodReason:
      'Interactive execution tracing with clear print statements demonstrates the exact order of execution.',
    strategiesAttempted: [
      {
        strategy: 'theory',
        strategyLabel: 'Theory',
        outcome: 'confused',
        timestamp: 'Turn 1',
        tutorExcerpt:
          'The finally block is guaranteed to execute upon try block completion, regardless of whether an unhandled exception or transfer of control (return, break) occurs.',
        studentResponse:
          '"Wait, if I return a value in try, how can finally run afterwards? Doesn\'t return mean the method is already finished?"',
      },
      {
        strategy: 'analogy',
        strategyLabel: 'Analogy',
        outcome: 'confused',
        timestamp: 'Turn 2',
        tutorExcerpt:
          'Think of checking out of a hotel room. Returning is packing your bag, but finally is handing the room key to the front desk before you walk out the front door.',
        studentResponse:
          '"I understand the metaphor, but what value actually comes out of the method in code?"',
      },
      {
        strategy: 'example',
        strategyLabel: 'Code Example',
        outcome: 'breakthrough',
        timestamp: 'Turn 3',
        tutorExcerpt:
          'Look at this trace: even though `return 10;` is hit, "Inside finally" prints BEFORE the caller receives 10!',
        studentResponse:
          '"Aha! Now I see the console output sequence. The return is queued, finally runs, then the result returns!"',
      },
    ],
    explanationSamples: {
      example: {
        strategy: 'example',
        title: 'Execution Trace with Return Statement',
        subtitle: 'Proving finally always runs',
        content: 'Observe the console output when a method returns inside `try`:',
        codeSnippet: `public static int testMethod() {
    try {
        System.out.println("1. Entering try block");
        return 100; // Value 100 is prepared for return
    } catch (Exception e) {
        System.out.println("Catch block");
    } finally {
        System.out.println("2. Finally block ALWAYS executes before exit!");
    }
    return 0;
}

// OUTPUT:
// 1. Entering try block
// 2. Finally block ALWAYS executes before exit!
// Caller receives: 100`,
      },
      analogy: {
        strategy: 'analogy',
        title: 'Real-World Analogy: The Restaurant Check',
        subtitle: 'Paying the bill before stepping out',
        content:
          'Returning from a method is like deciding to leave a restaurant. You can decide to leave early (`return`), but the restaurant manager will ensure the bill is paid (`finally`) before you walk out the door. The only way `finally` won\'t run is if an earthquake destroys the building (`System.exit(0)` or JVM crash)!',
      },
      simplified: {
        strategy: 'simplified',
        title: 'The 1 Unbreakable Rule',
        subtitle: 'Zero exceptions to this behavior',
        content:
          'â€¢ **The Rule:** If execution enters the `try` block, the `finally` block **WILL** run before the method exits, even if there is a `return` or error.\nâ€¢ **The Only Exception:** Calling `System.exit(0)` terminates the entire JVM.',
      },
      theory: {
        strategy: 'theory',
        title: 'Java Virtual Machine Specification Â§14.20.2',
        subtitle: 'Formal completion semantics',
        content:
          'Execution of a try-finally statement first executes the try block. If execution of the try block completes abruptly with a return value V, the finally block is executed. If the finally block completes normally, the try-finally statement completes abruptly with the return value V.',
      },
    },
    practiceQuestion: {
      question:
        'What will be the return value of a method if `try` returns 10 and `finally` returns 20?',
      options: [
        '10 (try return takes precedence)',
        '20 (finally return overrides the pending return)',
        'Compiler error (unreachable statement)',
        '15 (average)',
      ],
      correctIndex: 1,
      explanation:
        'A return statement in `finally` abruptly overrides any previously pending return or uncaught exception from the try block (warning: this is considered bad practice, but illustrates finally precedence).',
    },
  },
];
