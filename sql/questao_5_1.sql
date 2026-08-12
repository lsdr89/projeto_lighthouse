WITH calendario AS (
    SELECT
        data::date AS data,
        CASE EXTRACT(DOW FROM data)
            WHEN 0 THEN 'Domingo'
            WHEN 1 THEN 'Segunda-feira'
            WHEN 2 THEN 'Terça-feira'
            WHEN 3 THEN 'Quarta-feira'
            WHEN 4 THEN 'Quinta-feira'
            WHEN 5 THEN 'Sexta-feira'
            WHEN 6 THEN 'Sábado'
        END AS dia_semana
    FROM generate_series(
        (SELECT MIN(placed_at)::date FROM orders),
        CURRENT_DATE,
        INTERVAL '1 day'
    ) AS data
),

vendas_por_dia AS (
    SELECT
        placed_at::date AS data,
        SUM(total) AS valor_venda
    FROM orders
    WHERE channel = 'pos'
    GROUP BY placed_at::date
)

SELECT
    c.data,
    c.dia_semana,
    COALESCE(v.valor_venda, 0) AS valor_venda
FROM calendario c
LEFT JOIN vendas_por_dia v
    ON c.data = v.data
ORDER BY c.data;
