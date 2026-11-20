-- Las proporciones semanales están entre 0 y 1
SELECT week, topic_id FROM mart_weekly_topics WHERE share < 0 OR share > 1 OR papers > total_papers
