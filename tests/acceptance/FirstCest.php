<?php

class FirstCest
{
    public function _before(AcceptanceTester $I)
    {
    }

    // tests
    public function tryToTest(AcceptanceTester $I, \Codeception\Scenario $scenario)
    {
        $I->amOnPage('/');
        $I->see('POLÍTICA');

        switch ($scenario->current('env')) {
            case 'dev':
                for ($x = 1; $x <= 14; $x++) {
                    $I->see("embed$x");
                }
                break;
            case 'test':
                $I->amOnPage('/articulo/2019/9/articulo-con-todas-las-funcionalidades/');
                $I->see('Artículo con todas las funcionalidades');
                break;
            case 'prod':
                $I->amOnPage('/articulo/2019/10/algunas-cosas-que-hay-que-saber-para-votar/');
                $I->see('Algunas cosas que hay que saber para votar');
                break;
        }
    }
}
