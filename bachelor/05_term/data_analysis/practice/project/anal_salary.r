data <- read.csv("/Users/konstantinovivan/Desktop/анал_дан/ds_salary/datascience_salaries.csv")

View(data)

data <- data[data$salary_currency != "EUR", ]

levels(data$job_type)

data$job_title <- factor(data$job_title)
data$job_type <- factor(data$job_type)
data$experience_level <- factor(data$experience_level)
data$location <- factor(data$location)

data <- data[, -c(1, 6)]

str(data)

library(ggplot2)

hist.salary <- ggplot(data, aes(salary)) +
    geom_histogram(aes(y = ..density..), bins = 30, color = "black", fill = "red") +
    theme_bw() + labs(x = "Заработная плата", y = "Плотность")

hist.salary + stat_function(fun = dnorm,
              args = list(mean = mean(data$salary, na.rm = TRUE),
                          sd = sd(data$salary, na.rm = TRUE)),
              color = "blue", size = 2)
