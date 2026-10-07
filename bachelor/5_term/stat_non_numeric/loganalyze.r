tbl <- data.frame(
    expand.grid(
        D = factor(c(1,2), labels = c("tea", "coffee")),
        L = factor(c(1,2), labels = c("smart", "strength"))
    ),
    count = c(59, 96, 101, 44)
)

library(MASS)

saturated.model <- loglm(count ~ D:L, data = tbl)
coefficients(saturated.model)
fitted(saturated.model)


m1 <- loglm(count ~ M:C + C:A + A:M, data = tbl)
coefficients(m1)

fitted(m1)
