library("ggplot2")

ds_salaries <- read.csv("пр_1/salaries.csv")

salary_in_usd <- ds_salaries["salary_in_usd"]

p <- ggplot(salary_in_usd, aes(salary_in_usd))

p + geom_density(color = "#0437F2", size = 3)

p + geom_boxplot(notch = TRUE, color = "#0437F2", fill = "white")

p + geom_histogram(color = "#0437F2", fill = "white", size = 1)

colnames(salary_in_usd) = c("sl")

# 1

sum(Mod(mean(salary_in_usd$sl) - salary_in_usd$sl) / sd(salary_in_usd$sl) > 4.5) / 3698

# 2

for (i in 1:10) {
  rand_df <- sample(salary_in_usd$sl, size = 370, replace = TRUE)
  s <- (sum((rand_df - mean(rand_df)) ^ 2) / 369) ^ 0.5
  print(sum((Mod(mean(rand_df) - rand_df) / s) > 4) / 370)
}

# 3

sum(Mod(mean(rand_df) - rand_df) / sd(salary_in_usd$sl) > 4.5) / 3698

