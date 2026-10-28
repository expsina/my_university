library(outliers)

d <- read.csv("salaries.csv")

sample_d <- d[sample(nrow(d), size = 30), ]
salaries <- sample_d$salary_in_usd
sort(salaries)

boxplot(salaries)
hist(salaries, 
     breaks = seq(min(salaries), max(salaries), length.out = 6), 
     border = "#0437F2", col = "azure",
     main = "Заработная плата разработчиков в сфере Data Science",
     xlab = "Заработная плата в долларах США")

grubbs.test(salaries, opposite = FALSE)
grubbs.test(salaries, opposite = TRUE)
grubbs.test(salaries, type = 11)

dixon.test(salaries)
dixon.test(salaries, opposite = TRUE)

shapiro.test(salaries)

irwin_test <- function(data, alpha) {
  n <- length(data)
  mean_val <- mean(data)
  median_val <- median(data)
  
  mode_val <- as.numeric(names(sort(table(data), descreasing = TRUE)[1]))
  
  statistic <- (mean_val - median_val) / (mean_val - mode_val)
  
  critical_value <- qnorm(1 - alpha / 2, mean = 0, sd = 1)
  
  if (abs(statistic) > critical_value) {
    result <- list(statistic = statistic, conclusion = paste("Отвергаем Н0: Не нормальное распределение"))
  } else {
    result <- list(statistic = statistic, conclusion = paste("Принимаем Н0: Нормальное распределение"))
  }
  
  return(result)
}

irwin_test(salaries, alpha = 0.01)
irwin_test(salaries, alpha = 0.05)
