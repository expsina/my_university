library(dplyr)

ev_ebitda <- c(2, 4, 7, 10, 9, 6)
debt_ebitda <- c(4, 2, 6, 5, 7, 3)
names <- c("softline", "yandex", "cian", "severstal", "nornikel", "cr")

companies <- data.frame(names, ev_ebitda, debt_ebitda)
View(companies)
companies

M <- dist(scale(companies[, 2:3]))
hc <- hclust(M, method = "ward.D2")

plot(hc)

library(StatMatch)

M <- mahalanobis.dist(companies[, 2:3])
hc <- hclust(M, method = "median")
plot(hc)

