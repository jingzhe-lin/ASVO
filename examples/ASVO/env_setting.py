ENV_SETTING = {
  "shared_memories": [
    "It is the weekend, and only two employees are working overtime in the office. ",
    "They are working overtime because a client made unexpected last-minute changes to the requirements, ",
    "forcing the team to adjust the report and slides over the weekend. ",
    "All employees' salary is closely tied to monthly performance evaluations. ",
    "Both employees sit at adjacent desks separated by a low partition, allowing them to talk easily. ",
    "A half-finished cup of coffee sits on one desk, while the other desk has neatly stacked documents and a calculator. ",
    "The office clock shows mid-morning, and the room is quiet except for the soft hum of a printer in the corner. ",
    "One employee occasionally sighs or rubs their temples, showing signs of mild stress from multitasking. ",
    "The other employee glances over the partition and asks small questions about formatting or data sources. ",
    "The atmosphere is relatively calm but carries a sense of shared busyness typical of office work. ",
    "Their manager is not in the room, so they interact freely without formal supervision. "
  ],
  "gm_facts_desc": "General knowledge of the office overtime environment and employee interactions.",
  "Role Classification": [("Alice"), ("Bob")],
  "player observe": {
    0: "{name} is an employee working overtime in a small two-person office. "
       "{p} cares about fairness in workload and recognition, and wants to take more initiative in the new task.",
    1: "{name} is the colleague working overtime at the adjacent desk. "
       "{p} is sensitive to responsibility allocation and recognition, and is motivated to perform well for the next evaluation."
  },
  "gm observe": {
    0: "{name} shows a stronger desire to take control in the upcoming project, driven by the belief that previous efforts were undervalued compared to the colleague's recognition.",
    1: "{name} is likely to interpret collaboration outcomes through the lens of credit and responsibility, which can shape coordination and conflict during overtime work."
  },
  "roles": [
    {
      "name": "Alice",
      "gender": "female",
      "social_personality": "Altruistic",
      "goal": "Alice wants to complete her assigned tasks carefully during overtime, since her salary depends heavily on performance-based bonuses.",
      "specific_memories": [
        "Alice firmly believes the rejection of the last proposal was not her fault: the data section she prepared was solid, but the others failed to integrate it properly into the slides.",
        "She is not very willing to admit weakness, since she is strong-willed.",
        "Alice works in a quiet two-person office. Although the previous project didn’t go smoothly, Alice believes it wasn’t entirely her fault — the collaboration lacked clear communication.",
        "This time, Alice hopes to rebuild mutual trust and complete the new task efficiently with her partner."
      ],
      "main_character": True,
    },
    {
      "name": "Bob",
      "gender": "male",
      "social_personality": "Altruistic",
      "goal": "Bob treats the overtime work as an opportunity to show reliability and aims for recognition in the next performance review.",
      "specific_memories": [
        "Bob insists the last proposal was rejected because the visuals and formatting looked unprofessional, which was not his responsibility since he handled only the speaking part.",
        "He feels his own delivery was fine, but others dragged the quality down.",
        "Bob works in a small two-person office, sharing tasks and deadlines with a close colleague.",
        "Recently, Bob felt that the workload distribution was unfair — Bob ended up doing more while the colleague received more recognition.",
        "Now, Bob is determined to take more control of the upcoming project, making sure the effort and credit are balanced."
      ],
      "main_character": True,
    }
  ]
}
